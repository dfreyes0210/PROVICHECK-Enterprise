import streamlit as st
from utils.ui import aplicar_estilo, encabezado
from utils.data import listar_hojas_excel, cargar_hoja
from config import EXCEL_PATH

st.set_page_config(page_title="Administración - PROVICHECK", page_icon="⚙️", layout="wide")
aplicar_estilo(); encabezado()
st.title("⚙️ Administración")
st.caption("Validación inicial de la base maestra.")
st.write("Archivo Excel esperado:")
st.code(str(EXCEL_PATH))
hojas = listar_hojas_excel()
if hojas:
    st.success("Excel detectado correctamente.")
    st.write("Hojas encontradas:", hojas)
    hoja = st.selectbox("Seleccione una hoja para previsualizar", hojas)
    df = cargar_hoja(hoja)
    st.write(f"Registros: {len(df)}")
    st.dataframe(df.head(50), use_container_width=True)
else:
    st.error("No se detectó el Excel base.")
