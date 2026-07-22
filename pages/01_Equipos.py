import streamlit as st
import pandas as pd

from utils.ui import aplicar_estilo, encabezado, tarjeta_equipo_html, sidebar_pro
from utils.data import cargar_hoja

st.set_page_config(
    page_title="Equipos PRO - PROVICHECK",
    page_icon="🧪",
    layout="wide"
)

aplicar_estilo()

if not st.session_state.get('autenticado', False):
    st.warning('Inicie sesión desde la página principal.')
    st.stop()

sidebar_pro()
encabezado()

st.title("🧪 Equipos PRO")
st.caption("Gestión visual de equipos registrados en la base maestra.")

equipos = cargar_hoja("Equipos")

if equipos.empty:
    st.error("No se encontró información en la hoja Equipos.")
    st.stop()

total_equipos = len(equipos)
total_labs = equipos["laboratorio"].nunique() if "laboratorio" in equipos.columns else 0
total_estados = equipos["estado"].nunique() if "estado" in equipos.columns else 0

m1, m2, m3 = st.columns(3)
m1.metric("🧪 Equipos registrados", total_equipos)
m2.metric("🏭 Laboratorios", total_labs)
m3.metric("🛡️ Estados", total_estados)

st.divider()

col_buscar, col_lab, col_estado = st.columns([2, 1, 1])

with col_buscar:
    busqueda = st.text_input(
        "Buscar equipo",
        placeholder="Código, nombre, marca, modelo, serie o responsable"
    )

df = equipos.copy()

if "laboratorio" in df.columns:
    laboratorios = ["Todos"] + sorted(df["laboratorio"].dropna().astype(str).unique().tolist())
    with col_lab:
        laboratorio_sel = st.selectbox("Laboratorio", laboratorios)

    if laboratorio_sel != "Todos":
        df = df[df["laboratorio"].astype(str) == laboratorio_sel]

if "estado" in df.columns:
    estados = ["Todos"] + sorted(df["estado"].dropna().astype(str).unique().tolist())
    with col_estado:
        estado_sel = st.selectbox("Estado", estados)

    if estado_sel != "Todos":
        df = df[df["estado"].astype(str) == estado_sel]

if busqueda:
    mascara = df.astype(str).apply(
        lambda columna: columna.str.contains(busqueda, case=False, na=False)
    ).any(axis=1)
    df = df[mascara]

st.write(f"Equipos encontrados: **{len(df)}**")

st.divider()

if df.empty:
    st.warning("No se encontraron equipos con los filtros seleccionados.")
    st.stop()

columnas = st.columns(3)

for i, (_, fila) in enumerate(df.iterrows()):
    equipo = fila.to_dict()
    codigo = equipo.get("codigo_equipo", f"equipo_{i}")

    with columnas[i % 3]:
        st.markdown(
            tarjeta_equipo_html(equipo),
            unsafe_allow_html=True
        )

        if st.button(
            "📘 Abrir Hoja de Vida Digital",
            key=f"abrir_{codigo}_{i}",
            use_container_width=True
        ):
            st.session_state["equipo_seleccionado"] = equipo
            st.switch_page("pages/02_Hoja_de_Vida.py")