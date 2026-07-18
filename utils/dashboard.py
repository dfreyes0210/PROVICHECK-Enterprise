import pandas as pd

from utils.data import cargar_hoja
from utils.sqlite_consultas import (
    consultar_sesiones_verificacion,
    consultar_bitacora_equipo,
)


def obtener_kpis():
    equipos = cargar_hoja("Equipos")
    sesiones = consultar_sesiones_verificacion(100000)

    total_equipos = len(equipos)
    equipos_activos = 0

    if not equipos.empty and "estado" in equipos.columns:
        estados = equipos["estado"].astype(str).str.lower()
        equipos_activos = estados.str.contains(
            "activo|operativo|disponible",
            na=False,
        ).sum()

    total_verificaciones = len(sesiones)
    conformes = 0
    no_conformes = 0
    incompletas = 0

    if not sesiones.empty and "estado" in sesiones.columns:
        estados_sesion = sesiones["estado"].astype(str).str.strip().str.lower()
        conformes = (estados_sesion == "conforme").sum()
        no_conformes = (estados_sesion == "no conforme").sum()
        incompletas = (estados_sesion == "incompleta").sum()

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
        "verificaciones": int(total_verificaciones),
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
        .sort_values("cantidad", ascending=False)
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
        .sort_values("cantidad", ascending=False)
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
                "detalle": f"Se registran {no_conformes} sesión(es) no conforme(s).",
            }
        )

    if incompletas > 0:
        alertas.append(
            {
                "nivel": "warning",
                "titulo": "Verificaciones incompletas",
                "detalle": f"Se registran {incompletas} sesión(es) incompleta(s).",
            }
        )

    bitacora = consultar_bitacora_equipo(None, 100000)
    if not bitacora.empty:
        alertas.append(
            {
                "nivel": "info",
                "titulo": "Eventos registrados",
                "detalle": f"La bitácora contiene {len(bitacora)} evento(s).",
            }
        )

    return alertas[:limite]