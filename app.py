import streamlit as st
import plotly.express as px

from config import APP_NAME, VERSION, EXCEL_PATH
from database import crear_base_datos
from utils.ui import aplicar_estilo, encabezado, login_limpio
from utils.data import cargar_hoja, listar_hojas_excel

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilo()
crear_base_datos()

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    encabezado()
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.info("Acceso exclusivo para usuarios autorizados.")
        login_limpio()
    st.stop()

with st.sidebar:
    st.title("🧪 PROVICHECK")
    st.caption(VERSION)
    st.write(f"Usuario: **{st.session_state.get('usuario','')}**")

    st.divider()

    st.page_link("app.py", label="🏠 Inicio")
    st.page_link("pages/01_Equipos.py", label="🧪 Equipos")
    st.page_link("pages/02_Hoja_de_Vida.py", label="📘 Hoja de Vida")
    st.page_link("pages/03_Administracion.py", label="⚙️ Administración")
    st.page_link("pages/04_Verificaciones.py", label="✅ Verificaciones")

    st.divider()

    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

encabezado()

equipos = cargar_hoja("Equipos")
verificaciones = cargar_hoja("Verificaciones")
hojas = listar_hojas_excel()

st.subheader("Dashboard ejecutivo inicial")

if equipos.empty:
    st.error("No se encontró la hoja 'Equipos' en data/PROVICHECK_Base_Datos.xlsx.")
    st.stop()

total_equipos = len(equipos)

equipos_activos = (
    equipos[
        equipos["estado"]
        .astype(str)
        .str.lower()
        .str.contains("activo|operativo|disponible", na=False)
    ].shape[0]
    if "estado" in equipos.columns
    else 0
)

total_labs = equipos["laboratorio"].nunique() if "laboratorio" in equipos.columns else 0
total_verificaciones = len(verificaciones) if not verificaciones.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equipos registrados", total_equipos)
c2.metric("Equipos activos/operativos", equipos_activos)
c3.metric("Laboratorios", total_labs)
c4.metric("Verificaciones históricas", total_verificaciones)

st.divider()

col_a, col_b = st.columns([1.2, 1])

with col_a:
    st.markdown("### Equipos por laboratorio")
    if "laboratorio" in equipos.columns:
        conteo_lab = equipos["laboratorio"].fillna("Sin laboratorio").value_counts().reset_index()
        conteo_lab.columns = ["laboratorio", "cantidad"]

        fig = px.bar(
            conteo_lab,
            x="laboratorio",
            y="cantidad",
            text="cantidad",
        )
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("### Estado de equipos")
    if "estado" in equipos.columns:
        conteo_estado = equipos["estado"].fillna("Sin estado").value_counts().reset_index()
        conteo_estado.columns = ["estado", "cantidad"]

        fig2 = px.pie(
            conteo_estado,
            names="estado",
            values="cantidad",
            hole=0.45,
        )
        fig2.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.markdown("### Estado de la base maestra")
st.success(f"Excel conectado correctamente: {EXCEL_PATH.name}")
st.write("Hojas detectadas:", hojas)

st.markdown("### Estado de la base operativa")
st.success("SQLite inicializado correctamente: data/provicheck.db")

st.markdown("### Vista rápida de equipos")
st.dataframe(equipos.head(10), use_container_width=True)