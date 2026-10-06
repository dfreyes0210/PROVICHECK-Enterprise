import pandas as pd
import streamlit as st

from config import EXCEL_PATH


def cargar_hoja(nombre_hoja: str) -> pd.DataFrame:
    """
    Carga una hoja del archivo maestro de PROVICHECK.

    Esta función NO utiliza caché para garantizar que los cambios realizados
    en el archivo Excel sean visibles inmediatamente en los diferentes módulos
    de PROVICHECK.

    Esto es especialmente importante para información dinámica como:
    - Equipos
    - Equipos_Patrones
    - Puntos_Verificacion
    - Relacion_Equipo_Patron
    - Fechas de vencimiento
    - Estados de equipos y patrones
    """

    if not EXCEL_PATH.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(
            EXCEL_PATH,
            sheet_name=nombre_hoja,
        )

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        return df

    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def listar_hojas_excel():
    """
    Devuelve la lista de hojas disponibles en el archivo maestro.

    Esta función puede mantenerse en caché porque únicamente consulta
    los nombres de las hojas y no los datos operativos de PROVICHECK.
    """

    if not EXCEL_PATH.exists():
        return []

    try:
        return pd.ExcelFile(
            EXCEL_PATH
        ).sheet_names

    except Exception:
        return []


def cargar_usuarios() -> pd.DataFrame:
    """
    Lee la hoja Usuarios sin caché.

    Esto permite que cualquier cambio relacionado con usuarios,
    permisos o accesos sea aplicado inmediatamente.
    """

    if not EXCEL_PATH.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(
            EXCEL_PATH,
            sheet_name="Usuarios",
        )

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        return df

    except Exception:
        return pd.DataFrame()