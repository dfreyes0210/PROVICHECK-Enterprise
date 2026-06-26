import pandas as pd
import streamlit as st
from config import EXCEL_PATH

@st.cache_data(show_spinner=False)
def cargar_hoja(nombre_hoja: str) -> pd.DataFrame:
    if not EXCEL_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=nombre_hoja)
        df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def listar_hojas_excel():
    if not EXCEL_PATH.exists():
        return []
    try:
        return pd.ExcelFile(EXCEL_PATH).sheet_names
    except Exception:
        return []
