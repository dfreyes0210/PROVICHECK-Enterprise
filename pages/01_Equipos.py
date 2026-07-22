mport streamlit as st
import pandas as pd

from utils.ui import (
    aplicar_estilo,
    encabezado,
    pie_pagina,
    sidebar_pro,
    tarjeta_equipo_html,
)
from utils.data import cargar_hoja

st.set_page_config(
    page_title="Equipos PRO - PROVICHECK",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilo()

if not st.session_state.get("autenticado", False):
    st.warning("La sesión no está activa. Ingrese nuevamente desde el Dashboard.")
    st.page_link("app.py", label="🔐 Ir al inicio de sesión")
    st.stop()

sidebar_pro()
encabezado()

st.markdown("## 🧪 Gestión de equipos")
st.caption(
    "Consulta, filtra y abre la hoja de vida digital de los equipos registrados."
)

equipos = cargar_hoja("Equipos")

if equipos.empty:
    st.error("No se encontró información en la hoja Equipos.")
    st.stop()

equipos = equipos.copy()
equipos.columns = [str(columna).strip() for columna in equipos.columns]

for columna in equipos.columns:
    if equipos[columna].dtype == "object":
        equipos[columna] = equipos[columna].fillna("").astype(str).str.strip()

total_equipos = len(equipos)
total_labs = (
    equipos["laboratorio"].replace("", pd.NA).nunique()
    if "laboratorio" in equipos.columns
    else 0
)

estados_normalizados = (
    equipos["estado"].astype(str).str.lower()
    if "estado" in equipos.columns
    else pd.Series(dtype=str)
)

total_operativos = int(
    estados_normalizados.str.contains(
        r"activo|operativo|disponible",
        case=False,
        na=False,
        regex=True,
    ).sum()
)

total_criticos = 0
if "criticidad" in equipos.columns:
    total_criticos = int(
        equipos["criticidad"]
        .astype(str)
        .str.lower()
        .str.contains(r"alta|crítica|critica", na=False, regex=True)
        .sum()
    )

m1, m2, m3, m4 = st.columns(4)
m1.metric("Equipos registrados", total_equipos)
m2.metric("Equipos operativos", total_operativos)
m3.metric("Laboratorios", total_labs)
m4.metric("Criticidad alta", total_criticos)

st.divider()

st.markdown("### 🔎 Filtros de consulta")

col_buscar, col_lab, col_estado, col_criticidad = st.columns([2.2, 1, 1, 1])

with col_buscar:
    busqueda = st.text_input(
        "Buscar equipo",
        placeholder="Código, nombre, marca, modelo, serie, ubicación o responsable",
    ).strip()

df = equipos.copy()

with col_lab:
    if "laboratorio" in df.columns:
        laboratorios = ["Todos"] + sorted(
            valor
            for valor in df["laboratorio"].dropna().astype(str).unique().tolist()
            if valor.strip()
        )
        laboratorio_sel = st.selectbox("Laboratorio", laboratorios)
    else:
        laboratorio_sel = "Todos"
        st.selectbox("Laboratorio", ["Todos"], disabled=True)

with col_estado:
    if "estado" in df.columns:
        estados = ["Todos"] + sorted(
            valor
            for valor in df["estado"].dropna().astype(str).unique().tolist()
            if valor.strip()
        )
        estado_sel = st.selectbox("Estado", estados)
    else:
        estado_sel = "Todos"
        st.selectbox("Estado", ["Todos"], disabled=True)

with col_criticidad:
    if "criticidad" in df.columns:
        criticidades = ["Todas"] + sorted(
            valor
            for valor in df["criticidad"].dropna().astype(str).unique().tolist()
            if valor.strip()
        )
        criticidad_sel = st.selectbox("Criticidad", criticidades)
    else:
        criticidad_sel = "Todas"
        st.selectbox("Criticidad", ["Todas"], disabled=True)

if laboratorio_sel != "Todos" and "laboratorio" in df.columns:
    df = df[df["laboratorio"].astype(str) == laboratorio_sel]

if estado_sel != "Todos" and "estado" in df.columns:
    df = df[df["estado"].astype(str) == estado_sel]

if criticidad_sel != "Todas" and "criticidad" in df.columns:
    df = df[df["criticidad"].astype(str) == criticidad_sel]

if busqueda:
    columnas_busqueda = [
        columna
        for columna in [
            "codigo_equipo",
            "nombre_equipo",
            "marca",
            "modelo",
            "serie",
            "laboratorio",
            "ubicacion",
            "responsable",
            "tipo_equipo",
        ]
        if columna in df.columns
    ]

    if columnas_busqueda:
        mascara = df[columnas_busqueda].astype(str).apply(
            lambda columna: columna.str.contains(
                busqueda,
                case=False,
                na=False,
                regex=False,
            )
        ).any(axis=1)
        df = df[mascara]

col_resultado, col_vista = st.columns([3, 1])

with col_resultado:
    st.markdown(
        f"**Resultado:** {len(df)} de {total_equipos} equipos encontrados."
    )

with col_vista:
    cantidad_columnas = st.selectbox(
        "Tarjetas por fila",
        [3, 2, 4],
        index=0,
    )

st.divider()

if df.empty:
    st.warning("No se encontraron equipos con los filtros seleccionados.")
    pie_pagina()
    st.stop()

columnas = st.columns(cantidad_columnas)

for indice, (_, fila) in enumerate(df.iterrows()):
    equipo = fila.to_dict()
    codigo = str(
        equipo.get("codigo_equipo", f"equipo_{indice}")
    ).strip() or f"equipo_{indice}"

    with columnas[indice % cantidad_columnas]:
        st.markdown(
            tarjeta_equipo_html(equipo),
            unsafe_allow_html=True,
        )

        if st.button(
            "📘 Abrir Hoja de Vida",
            key=f"abrir_{codigo}_{indice}",
            width="stretch",
        ):
            st.session_state["equipo_seleccionado"] = equipo
            st.switch_page("pages/02_Hoja_de_Vida.py")

pie_pagina()