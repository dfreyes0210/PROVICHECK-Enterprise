
"""PROVICHECK | Preparación de informe global PA.

Solo lectura, acceso gestor.

Metodologías:
- Referencia interlaboratorio Cenicaña 2026.
- Desviación estándar de resultados individuales.
- Desviación estándar de promedios por analista.

Los resultados del informe se entregan anonimizados.
La relación entre códigos e identidades se mantiene separada.
"""

from __future__ import annotations

import math
import re
import unicodedata

from utils.pruebas_aptitud_db import (
    identidad,
    listar_materiales,
    listar_parametros_registro,
)
from utils.supabase_client import obtener_cliente_supabase
from utils.data import cargar_hoja
from utils.pruebas_aptitud_estadistica import evaluar_parametro


METODOS = {
    "cenicana": "Referencia interlaboratorio Cenicaña 2026",
    "individuales": "Desviación estándar de resultados individuales",
    "promedios": "Desviación estándar de promedios por analista",
}


def normalizar(valor):
    """Normaliza textos y reconoce valores vacíos de pandas."""

    if valor is None:
        return ""

    try:
        if math.isnan(float(valor)):
            return ""
    except (TypeError, ValueError, OverflowError):
        pass

    texto = " ".join(str(valor).casefold().split())

    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def _nombre_ensayo(nombre):
    """Obtiene el nombre del ensayo sin método ni unidad."""

    texto = normalizar(nombre)

    # Ejemplos:
    # Polarización (°Z) -> polarizacion
    # Color (UI) -> color
    texto = re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        texto,
    )

    # Ejemplos:
    # Humedad - Método A -> humedad
    # Humedad — Método B -> humedad
    texto = re.sub(
        r"\s*[-–—]\s*metodo\s*[ab]\s*$",
        "",
        texto,
    )

    equivalencias = {
        "pol": "polarizacion",
        "pol aparente": "polarizacion",
        "polarizacion aparente": "polarizacion",
    }

    return equivalencias.get(texto, texto)


def _metodo_ensayo(nombre):
    """Identifica métodos A y B en el nombre del ensayo."""

    texto = normalizar(nombre)

    coincidencia = re.search(
        r"metodo\s*([ab])\s*$",
        texto,
    )

    if coincidencia:
        return f"metodo {coincidencia.group(1)}"

    return ""


def _normalizar_metodo(valor):
    """Normaliza el método del Excel maestro."""

    texto = normalizar(valor)

    if texto in {
        "",
        "nan",
        "none",
        "no aplica",
        "n/a",
        "na",
    }:
        return ""

    coincidencia = re.fullmatch(
        r"(?:metodo\s*)?([ab])",
        texto,
    )

    if coincidencia:
        return f"metodo {coincidencia.group(1)}"

    return texto


def _referencias():
    """Carga las referencias de Cenicaña desde el Excel maestro."""

    df = cargar_hoja("PA_Desviaciones")

    obligatorias = {
        "Año",
        "Material",
        "Parámetro",
        "Método",
        "σpt",
        "Unidad",
    }

    if df.empty or not obligatorias.issubset(df.columns):
        raise ValueError(
            "PA_Desviaciones está vacía o le faltan "
            "columnas requeridas."
        )

    return df.to_dict("records")


def _referencia(material, parametro, unidad, refs):
    """Busca una única referencia externa para material y ensayo.

    La búsqueda exige coincidencia de:
    - Año 2026.
    - Material.
    - Ensayo.
    - Método, cuando corresponda.
    - Unidad.

    No permite confundir Humedad Método A con Método B.
    """

    nombre = _nombre_ensayo(parametro)
    metodo = _metodo_ensayo(parametro)
    unidad_normalizada = normalizar(unidad)

    candidatos = []

    for registro in refs:
        try:
            if int(registro["Año"]) != 2026:
                continue

            if normalizar(registro["Material"]) != normalizar(material):
                continue

            if _nombre_ensayo(registro["Parámetro"]) != nombre:
                continue

            metodo_excel = _normalizar_metodo(
                registro.get("Método")
            )

            # El método debe coincidir exactamente.
            # Un método vacío solo coincide con otro vacío.
            if metodo_excel != metodo:
                continue

            if normalizar(registro.get("Unidad")) != unidad_normalizada:
                continue

            sigma = float(registro["σpt"])

            if math.isfinite(sigma) and sigma > 0:
                candidatos.append(sigma)

        except (
            ValueError,
            TypeError,
            OverflowError,
            KeyError,
        ):
            continue

    if len(candidatos) != 1:
        raise ValueError(
            "Referencia Cenicaña no única o ausente: "
            f"{material} / {parametro} ({unidad}). "
            f"Coincidencias: {len(candidatos)}"
        )

    return candidatos[0]


def preparar_informe_global(campana, metodo):
    """Prepara los datos anonimizados del informe global.

    No escribe ni modifica información en Supabase.

    Retorna:
        datos_campana
        materiales
        lista_nombres
        confidencial
        advertencias
    """

    identidad(gestor=True)

    if metodo not in METODOS:
        raise ValueError("Metodología no reconocida.")

    cid = int(campana["id"])

    db = obtener_cliente_supabase()

    participaciones = (
        db.table("pa_participaciones")
        .select("id,id_usuario")
        .eq("campana_id", cid)
        .order("id")
        .execute()
    ).data or []

    # Códigos anónimos estables dentro de la campaña.
    mapa = {
        str(participacion["id_usuario"]): f"PA-{i:03d}"
        for i, participacion in enumerate(participaciones, 1)
    }

    usuarios_df = cargar_hoja("Usuarios")

    nombres = {}

    if (
        not usuarios_df.empty
        and {"id_usuario", "nombre_usuario"}.issubset(
            usuarios_df.columns
        )
    ):
        nombres = {
            str(registro["id_usuario"]).strip():
            str(registro["nombre_usuario"]).strip()
            for registro in usuarios_df.to_dict("records")
        }

    lista_nombres = [
        nombres.get(usuario, "Participante registrado")
        for usuario in mapa
    ]

    confidencial = [
        {
            "codigo": codigo,
            "id_usuario": usuario,
            "nombre": nombres.get(
                usuario,
                "No disponible",
            ),
        }
        for usuario, codigo in mapa.items()
    ]

    # Las referencias externas se consultan únicamente
    # cuando se selecciona la metodología Cenicaña.
    refs = (
        _referencias()
        if metodo == "cenicana"
        else []
    )

    materiales = []
    advertencias = []

    for material in listar_materiales(cid):

        ensayos = []

        for parametro in listar_parametros_registro(
            material["id"]
        ):

            reporte = evaluar_parametro(
                cid,
                material["id"],
                parametro["id"],
                None,
            )

            sigma = None

            if metodo == "cenicana":

                try:
                    sigma = _referencia(
                        material["nombre"],
                        parametro["nombre"],
                        parametro.get("unidad", ""),
                        refs,
                    )

                except ValueError as error:
                    advertencias.append(str(error))

            elif metodo == "individuales":

                sigma = reporte.get(
                    "desviacion_resultados_individuales"
                )

            elif metodo == "promedios":

                sigma = reporte.get(
                    "desviacion_promedios_participantes"
                )

            if (
                sigma is not None
                and math.isfinite(float(sigma))
                and float(sigma) > 0
            ):

                # Se utiliza el motor estadístico existente
                # para mantener los mismos criterios de z-score.
                reporte = evaluar_parametro(
                    cid,
                    material["id"],
                    parametro["id"],
                    float(sigma),
                )

            else:

                sigma = None

                advertencias.append(
                    "Sin dispersión válida: "
                    f"{material['nombre']} / "
                    f"{parametro['nombre']}"
                )

            filas = []

            for fila in reporte["resultados"]:

                usuario = fila.get("id_usuario")

                if usuario not in mapa:
                    raise ValueError(
                        "Resultado sin participación "
                        "registrada en campaña."
                    )

                fila_anonima = {
                    clave: valor
                    for clave, valor in fila.items()
                    if clave != "id_usuario"
                }

                fila_anonima["codigo_anonimo"] = mapa[
                    usuario
                ]

                filas.append(fila_anonima)

            reporte["resultados"] = filas

            # Este indicador conserva la compatibilidad
            # con el generador PDF actual.
            # No representa aprobación metrológica formal.
            reporte["sigma_pt_aprobada"] = bool(sigma)

            reporte["metodologia_sigma"] = METODOS[
                metodo
            ]

            ensayos.append(reporte)

        materiales.append(
            {
                "nombre": material["nombre"],
                "ensayos": ensayos,
            }
        )

    datos_campana = {
        clave: campana.get(clave)
        for clave in (
            "codigo",
            "titulo",
            "fecha_apertura",
            "fecha_cierre",
        )
    }

    datos_campana["metodologia_sigma"] = METODOS[
        metodo
    ]

    return (
        datos_campana,
        materiales,
        lista_nombres,
        confidencial,
        advertencias,
    )
