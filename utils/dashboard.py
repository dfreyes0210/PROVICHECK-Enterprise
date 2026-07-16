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

    return {
        "equipos": total_equipos,
        "activos": equipos_activos,
        "verificaciones": verificaciones,
        "conformes": conformes,
        "no_conformes": no_conformes,
        "incompletas": incompletas,
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