import pandas as pd

from utils.data import cargar_hoja
from utils.sqlite_consultas import (
    consultar_historial_equipo,
    consultar_sesiones_verificacion,
    consultar_bitacora_equipo,
)


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
            .str.contains("activo|operativo|disponible")
        ].shape[0]

    verificaciones = len(sesiones)

    conformes = 0
    no_conformes = 0
    incompletas = 0

    if not sesiones.empty:

        conformes = (sesiones["estado"] == "Conforme").sum()

        no_conformes = (sesiones["estado"] == "No conforme").sum()

        incompletas = (sesiones["estado"] == "Incompleta").sum()

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

    if equipos.empty:
        return pd.DataFrame()

    return (
        equipos.groupby("laboratorio")
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )


def obtener_estado_equipos():

    equipos = cargar_hoja("Equipos")

    if equipos.empty:
        return pd.DataFrame()

    return (
        equipos.groupby("estado")
        .size()
        .reset_index(name="cantidad")
    )


def obtener_estado_verificaciones():

    sesiones = consultar_sesiones_verificacion(100000)

    if sesiones.empty:
        return pd.DataFrame()

    return (
        sesiones.groupby("estado")
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

    if equipos.empty:
        return pd.DataFrame()

    columnas = [
        "codigo_equipo",
        "nombre_equipo",
        "laboratorio",
        "frecuencia_verificacion",
    ]

    existentes = [
        c for c in columnas
        if c in equipos.columns
    ]

    return equipos[existentes]