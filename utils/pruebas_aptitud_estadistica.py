
"""PROVICHECK | Evaluación estadística de pruebas de aptitud.

Resultados reales y simulación de cinco participantes.

Criterios:
- Dispersión principal: desviación estándar muestral de todos
  los resultados individuales válidos.
- Dispersión secundaria: desviación estándar muestral de los
  promedios de los participantes con duplicados completos.
- Valor asignado: mediana de los promedios por participante.
- Puntuación z: promedio individual frente al valor asignado,
  dividido entre la desviación estándar de evaluación (sigma_pt).

Archivo: utils/pruebas_aptitud_estadistica.py
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from statistics import median, stdev
from typing import Any

from utils.pruebas_aptitud_db import identidad
from utils.supabase_client import obtener_cliente_supabase


def _numero(valor: Any) -> float | None:
    """Convierte un valor numérico finito a float."""
    if valor is None or str(valor).strip() == "":
        return None

    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None

    return float(numero) if numero.is_finite() else None


def _desviacion_muestral(valores: list[float]) -> float | None:
    """Calcula la desviación estándar muestral si hay dos o más datos."""
    return stdev(valores) if len(valores) >= 2 else None


def _evaluar_filas(
    filas: list[dict],
    desviacion_evaluacion: float | None,
) -> dict:
    """Calcula los indicadores y clasifica los participantes."""

    sigma = _numero(desviacion_evaluacion)

    if desviacion_evaluacion is not None and (
        sigma is None or sigma <= 0
    ):
        raise ValueError(
            "La desviación estándar de evaluación debe ser positiva."
        )

    # Opción 2: todos los resultados individuales disponibles.
    resultados_individuales = []

    for fila in filas:
        for campo in ("resultado_1", "resultado_2"):
            valor = fila.get(campo)
            if valor is not None:
                resultados_individuales.append(valor)

    desviacion_individuales = _desviacion_muestral(
        resultados_individuales
    )

    # Opción 1: promedios de participantes con duplicados completos.
    promedios = [
        fila["promedio"]
        for fila in filas
        if fila["promedio"] is not None
    ]

    desviacion_promedios = _desviacion_muestral(promedios)

    # El valor asignado conserva la metodología aprobada.
    asignado = median(promedios) if promedios else None

    for fila in filas:
        promedio = fila["promedio"]

        z = (
            (promedio - asignado) / sigma
            if promedio is not None
            and asignado is not None
            and sigma is not None
            else None
        )

        fila["z_score"] = z

        fila["clasificacion"] = (
            "Sin evaluar" if z is None
            else "Satisfactorio" if abs(z) <= 2
            else "Cuestionable" if abs(z) < 3
            else "No satisfactorio"
        )

    return {
        "resultados": filas,
        "participantes_con_resultados": len(filas),
        "participantes_con_duplicados_completos": len(promedios),
        "numero_resultados_individuales": len(resultados_individuales),
        "valor_asignado_mediana": asignado,

        # Indicador principal, manteniendo la clave utilizada
        # actualmente por el dashboard y el informe PDF.
        "desviacion_observada_muestral": desviacion_individuales,

        # Claves explícitas para los nuevos indicadores.
        "desviacion_resultados_individuales": desviacion_individuales,
        "desviacion_promedios_participantes": desviacion_promedios,

        # Criterio independiente para la puntuación z.
        "desviacion_evaluacion": sigma,
    }


def evaluar_parametro(
    campana_id: int,
    material_id: int,
    parametro_id: int,
    desviacion_evaluacion: float | None = None,
) -> dict:
    """Evalúa exclusivamente resultados enviados definitivamente."""

    identidad(gestor=True)

    cid = int(campana_id)
    mid = int(material_id)
    pid = int(parametro_id)

    if min(cid, mid, pid) <= 0:
        raise ValueError("Identificadores inválidos.")

    db = obtener_cliente_supabase()

    materiales = (
        db.table("pa_materiales")
        .select("id,campana_id,nombre")
        .eq("id", mid)
        .eq("campana_id", cid)
        .limit(1)
        .execute()
    ).data or []

    if not materiales:
        raise ValueError("El material no pertenece a la campaña.")

    parametros = (
        db.table("pa_parametros")
        .select("id,material_id,nombre,unidad,decimales")
        .eq("id", pid)
        .eq("material_id", mid)
        .limit(1)
        .execute()
    ).data or []

    if not parametros:
        raise ValueError("El parámetro no pertenece al material.")

    participaciones = (
        db.table("pa_participaciones")
        .select("id,id_usuario")
        .eq("campana_id", cid)
        .execute()
    ).data or []

    participantes = {
        int(p["id"]): str(p["id_usuario"])
        for p in participaciones
    }

    entregas = (
        db.table("pa_entregas_material")
        .select("id,participacion_id")
        .eq("material_id", mid)
        .eq("estado", "enviado")
        .execute()
    ).data or []

    entregas_por_id = {
        int(e["id"]): participantes[int(e["participacion_id"])]
        for e in entregas
        if int(e["participacion_id"]) in participantes
    }

    filas = []

    if entregas_por_id:
        resultados = (
            db.table("pa_resultados")
            .select(
                "entrega_id,parametro_id,resultado_1,resultado_2"
            )
            .eq("parametro_id", pid)
            .in_("entrega_id", list(entregas_por_id))
            .execute()
        ).data or []

        for resultado in resultados:
            usuario = entregas_por_id.get(
                int(resultado["entrega_id"])
            )

            if usuario is None:
                continue

            a = _numero(resultado.get("resultado_1"))
            b = _numero(resultado.get("resultado_2"))

            promedio = (
                (a + b) / 2
                if a is not None and b is not None
                else None
            )

            filas.append({
                "id_usuario": usuario,
                "resultado_1": a,
                "resultado_2": b,
                "promedio": promedio,
            })

    filas.sort(key=lambda fila: fila["id_usuario"])

    indicadores = _evaluar_filas(
        filas,
        desviacion_evaluacion,
    )

    return {
        "campana_id": cid,
        "material": materiales[0]["nombre"],
        "parametro": parametros[0]["nombre"],
        "unidad": parametros[0].get("unidad", ""),
        "decimales": parametros[0].get("decimales", 2),
        **indicadores,
    }


def evaluar_simulacion_color(
    desviacion_evaluacion: float | None = None,
) -> dict:
    """Simulación en memoria. No escribe datos en Supabase."""

    identidad(gestor=True)

    datos = [
        ("SIM-001", 150, 152),
        ("SIM-002", 148, 150),
        ("SIM-003", 153, 155),
        ("SIM-004", 147, 149),
        ("SIM-005", 165, 167),
    ]

    filas = [
        {
            "id_usuario": usuario,
            "resultado_1": float(a),
            "resultado_2": float(b),
            "promedio": (a + b) / 2,
        }
        for usuario, a, b in datos
    ]

    indicadores = _evaluar_filas(
        filas,
        desviacion_evaluacion,
    )

    return {
        "campana_id": None,
        "material": "AZÚCAR BLANCO (SIMULACIÓN)",
        "parametro": "Color",
        "unidad": "UI",
        "decimales": 2,
        **indicadores,
    }
