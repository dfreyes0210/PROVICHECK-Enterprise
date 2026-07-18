import re
from datetime import date

import pandas as pd

from utils.data import cargar_hoja
from utils.sqlite_consultas import (
    consultar_sesiones_verificacion,
    consultar_bitacora_equipo,
)


def _normalizar_texto(valor):
    return str(valor or "").strip().lower()


def _buscar_columna(df, opciones):
    mapa = {str(col).strip().lower(): col for col in df.columns}
    for opcion in opciones:
        if opcion.lower() in mapa:
            return mapa[opcion.lower()]
    return None


def _frecuencia_a_dias(valor):
    texto = _normalizar_texto(valor)

    if not texto or texto in {"nan", "none", "sin definir"}:
        return None

    equivalencias = {
        "diaria": 1,
        "diario": 1,
        "semanal": 7,
        "quincenal": 15,
        "mensual": 30,
        "bimestral": 60,
        "trimestral": 90,
        "cuatrimestral": 120,
        "semestral": 180,
        "anual": 365,
    }

    for nombre, dias in equivalencias.items():
        if nombre in texto:
            return dias

    numero = re.search(r"(\d+)", texto)
    if not numero:
        return None

    cantidad = int(numero.group(1))

    if "día" in texto or "dia" in texto:
        return cantidad
    if "semana" in texto:
        return cantidad * 7
    if "mes" in texto:
        return cantidad * 30
    if "año" in texto or "ano" in texto:
        return cantidad * 365

    return cantidad


def obtener_kpis():
    equipos = cargar_hoja("Equipos")
    sesiones = consultar_sesiones_verificacion(100000)

    total_equipos = len(equipos)
    equipos_activos = 0

    if "estado" in equipos.columns:
        equipos_activos = equipos[
            equipos["estado"]
            .astype(str)
            .str.lower()
            .str.contains("activo|operativo|disponible", na=False)
        ].shape[0]

    verificaciones = len(sesiones)
    conformes = 0
    no_conformes = 0
    incompletas = 0

    if not sesiones.empty and "estado" in sesiones.columns:
        estados = sesiones["estado"].astype(str).str.strip().str.lower()
        conformes = int((estados == "conforme").sum())
        no_conformes = int((estados == "no conforme").sum())
        incompletas = int((estados == "incompleta").sum())

    sesiones_cerradas = conformes + no_conformes
    porcentaje_conformidad = (
        round((conformes / sesiones_cerradas) * 100, 1)
        if sesiones_cerradas > 0
        else 0.0
    )

    alertas = no_conformes + incompletas

    return {
        "equipos": int(total_equipos),
        "activos": int(equipos_activos),
        "verificaciones": int(verificaciones),
        "conformes": int(conformes),
        "no_conformes": int(no_conformes),
        "incompletas": int(incompletas),
        "alertas": int(alertas),
        "porcentaje_conformidad": porcentaje_conformidad,
    }


def obtener_ultimas_verificaciones(limite=10):
    return consultar_sesiones_verificacion(limite)


def obtener_bitacora_reciente(limite=10):
    return consultar_bitacora_equipo(None, limite)


def obtener_equipos_por_laboratorio():
    equipos = cargar_hoja("Equipos")

    if equipos.empty or "laboratorio" not in equipos.columns:
        return pd.DataFrame(columns=["laboratorio", "cantidad"])

    return (
        equipos.assign(
            laboratorio=equipos["laboratorio"].fillna("Sin laboratorio")
        )
        .groupby("laboratorio")
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )


def obtener_estado_equipos():
    equipos = cargar_hoja("Equipos")

    if equipos.empty or "estado" not in equipos.columns:
        return pd.DataFrame(columns=["estado", "cantidad"])

    return (
        equipos.assign(estado=equipos["estado"].fillna("Sin estado"))
        .groupby("estado")
        .size()
        .reset_index(name="cantidad")
    )


def obtener_estado_verificaciones():
    sesiones = consultar_sesiones_verificacion(100000)

    if sesiones.empty or "estado" not in sesiones.columns:
        return pd.DataFrame(columns=["estado", "cantidad"])

    return (
        sesiones.assign(estado=sesiones["estado"].fillna("Sin estado"))
        .groupby("estado")
        .size()
        .reset_index(name="cantidad")
    )


def obtener_alertas(limite=5):
    sesiones = consultar_sesiones_verificacion(100000)
    alertas = []

    if sesiones.empty or "estado" not in sesiones.columns:
        return alertas

    estados = sesiones["estado"].astype(str).str.strip().str.lower()
    no_conformes = int((estados == "no conforme").sum())
    incompletas = int((estados == "incompleta").sum())

    if no_conformes > 0:
        alertas.append(
            {
                "nivel": "error",
                "titulo": "Verificaciones no conformes",
                "detalle": (
                    f"Se registran {no_conformes} "
                    "sesión(es) no conforme(s)."
                ),
            }
        )

    if incompletas > 0:
        alertas.append(
            {
                "nivel": "warning",
                "titulo": "Verificaciones incompletas",
                "detalle": (
                    f"Se registran {incompletas} "
                    "sesión(es) incompleta(s)."
                ),
            }
        )

    return alertas[:limite]


def obtener_proximas_verificaciones():
    equipos = cargar_hoja("Equipos")
    sesiones = consultar_sesiones_verificacion(100000)

    if equipos.empty:
        return pd.DataFrame()

    col_codigo = _buscar_columna(
        equipos,
        ["codigo_equipo", "código_equipo", "codigo", "código"],
    )
    col_nombre = _buscar_columna(
        equipos,
        ["nombre_equipo", "equipo", "nombre"],
    )
    col_laboratorio = _buscar_columna(
        equipos,
        ["laboratorio"],
    )
    col_frecuencia = _buscar_columna(
        equipos,
        [
            "frecuencia_verificacion",
            "frecuencia_verificación",
            "frecuencia",
        ],
    )

    if col_codigo is None:
        return pd.DataFrame()

    salida = pd.DataFrame()
    salida["codigo_equipo"] = equipos[col_codigo].astype(str).str.strip()
    salida["nombre_equipo"] = (
        equipos[col_nombre].fillna("Sin nombre").astype(str)
        if col_nombre is not None
        else "Sin nombre"
    )
    salida["laboratorio"] = (
        equipos[col_laboratorio].fillna("Sin laboratorio").astype(str)
        if col_laboratorio is not None
        else "Sin laboratorio"
    )
    salida["frecuencia"] = (
        equipos[col_frecuencia].fillna("Sin definir").astype(str)
        if col_frecuencia is not None
        else "Sin definir"
    )

    salida["ultima_verificacion"] = pd.NaT

    if not sesiones.empty:
        ses_codigo = _buscar_columna(
            sesiones,
            ["codigo_equipo", "código_equipo", "codigo", "código"],
        )
        ses_fecha = _buscar_columna(
            sesiones,
            ["fecha", "fecha_verificacion", "fecha_verificación"],
        )

        if ses_codigo is not None and ses_fecha is not None:
            historial = sesiones[[ses_codigo, ses_fecha]].copy()
            historial[ses_codigo] = historial[ses_codigo].astype(str).str.strip()
            historial[ses_fecha] = pd.to_datetime(
                historial[ses_fecha],
                errors="coerce",
                dayfirst=True,
            )

            ultimas = (
                historial.dropna(subset=[ses_fecha])
                .groupby(ses_codigo)[ses_fecha]
                .max()
            )

            salida["ultima_verificacion"] = salida["codigo_equipo"].map(ultimas)

    salida["dias_frecuencia"] = salida["frecuencia"].apply(_frecuencia_a_dias)
    salida["proxima_verificacion"] = salida.apply(
        lambda fila: (
            fila["ultima_verificacion"]
            + pd.to_timedelta(fila["dias_frecuencia"], unit="D")
            if pd.notna(fila["ultima_verificacion"])
            and pd.notna(fila["dias_frecuencia"])
            else pd.NaT
        ),
        axis=1,
    )

    hoy = pd.Timestamp(date.today())

    def clasificar(fila):
        proxima = fila["proxima_verificacion"]

        if pd.isna(fila["dias_frecuencia"]):
            return "⚪ Sin frecuencia"

        if pd.isna(fila["ultima_verificacion"]):
            return "🔴 Sin verificar"

        dias = int((proxima.normalize() - hoy).days)

        if dias < 0:
            return "🔴 Vencida"
        if dias <= 7:
            return "🟡 Próxima"
        return "🟢 Vigente"

    salida["estado_programacion"] = salida.apply(clasificar, axis=1)

    orden = {
        "🔴 Vencida": 1,
        "🔴 Sin verificar": 2,
        "🟡 Próxima": 3,
        "🟢 Vigente": 4,
        "⚪ Sin frecuencia": 5,
    }

    salida["orden"] = salida["estado_programacion"].map(orden).fillna(9)

    return (
        salida.sort_values(
            ["orden", "proxima_verificacion", "codigo_equipo"],
            na_position="last",
        )
        .drop(columns=["dias_frecuencia", "orden"])
        .reset_index(drop=True)
    )


def obtener_estado_general():
    programacion = obtener_proximas_verificaciones()
    kpis = obtener_kpis()

    vencidas = 0
    sin_verificar = 0
    proximas = 0

    if not programacion.empty and "estado_programacion" in programacion.columns:
        estados = programacion["estado_programacion"].astype(str)
        vencidas = int(estados.str.contains("Vencida", na=False).sum())
        sin_verificar = int(estados.str.contains("Sin verificar", na=False).sum())
        proximas = int(estados.str.contains("Próxima", na=False).sum())

    criticas = vencidas + sin_verificar + kpis["no_conformes"]

    if criticas > 0:
        return {
            "nivel": "error",
            "estado": "🔴 Acción inmediata",
            "detalle": (
                f"{vencidas} vencida(s), {sin_verificar} sin verificar y "
                f'{kpis["no_conformes"]} no conforme(s).'
            ),
        }

    if proximas > 0 or kpis["incompletas"] > 0:
        return {
            "nivel": "warning",
            "estado": "🟡 Requiere atención",
            "detalle": (
                f"{proximas} verificación(es) próxima(s) y "
                f'{kpis["incompletas"]} incompleta(s).'
            ),
        }

    return {
        "nivel": "success",
        "estado": "🟢 Operación controlada",
        "detalle": "No se identifican alertas críticas de programación.",
    }