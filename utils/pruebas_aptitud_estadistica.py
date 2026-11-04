
"""PROVICHECK | Evaluación estadística de pruebas de aptitud.
Fase 5B: resultados reales y simulación de cinco participantes.
Archivo: utils/pruebas_aptitud_estadistica.py
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from statistics import median, stdev
from typing import Any

from utils.pruebas_aptitud_db import identidad
from utils.supabase_client import obtener_cliente_supabase


def _numero(valor: Any) -> float | None:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        n = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return float(n) if n.is_finite() else None


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

        for r in resultados:
            usuario = entregas_por_id.get(int(r["entrega_id"]))

            if usuario is None:
                continue

            a = _numero(r.get("resultado_1"))
            b = _numero(r.get("resultado_2"))

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

    filas.sort(key=lambda x: x["id_usuario"])

    valores = [
        f["promedio"]
        for f in filas
        if f["promedio"] is not None
    ]

    asignado = median(valores) if valores else None
    dispersion = stdev(valores) if len(valores) >= 2 else None

    sigma = _numero(desviacion_evaluacion)

    if desviacion_evaluacion is not None and (
        sigma is None or sigma <= 0
    ):
        raise ValueError(
            "La desviación estándar de evaluación debe ser positiva."
        )

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
        "campana_id": cid,
        "material": materiales[0]["nombre"],
        "parametro": parametros[0]["nombre"],
        "unidad": parametros[0].get("unidad", ""),
        "decimales": parametros[0].get("decimales", 2),
        "participantes_con_resultados": len(filas),
        "participantes_con_duplicados_completos": len(valores),
        "valor_asignado_mediana": asignado,
        "desviacion_observada_muestral": dispersion,
        "desviacion_evaluacion": sigma,
        "resultados": filas,
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

    sigma = _numero(desviacion_evaluacion)

    if desviacion_evaluacion is not None and (
        sigma is None or sigma <= 0
    ):
        raise ValueError(
            "La desviación de evaluación debe ser positiva."
        )

    filas = [
        {
            "id_usuario": usuario,
            "resultado_1": float(a),
            "resultado_2": float(b),
            "promedio": (a + b) / 2,
        }
        for usuario, a, b in datos
    ]

    valores = [fila["promedio"] for fila in filas]
    asignado = median(valores)

    for fila in filas:
        z = (
            (fila["promedio"] - asignado) / sigma
            if sigma is not None
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
        "campana_id": None,
        "material": "AZÚCAR BLANCO (SIMULACIÓN)",
        "parametro": "Color",
        "unidad": "UI",
        "decimales": 2,
        "participantes_con_resultados": len(filas),
        "participantes_con_duplicados_completos": len(valores),
        "valor_asignado_mediana": asignado,
        "desviacion_observada_muestral": stdev(valores),
        "desviacion_evaluacion": sigma,
        "resultados": filas,
    }
