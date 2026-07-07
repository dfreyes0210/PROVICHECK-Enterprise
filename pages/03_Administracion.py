import streamlit as st

from utils.ui import aplicar_estilo, encabezado
from utils.sqlite_consultas import (
    consultar_sesiones_verificacion,
    consultar_detalle_sesion,
    consultar_bitacora_equipo,
)

st.set_page_config(
    page_title="Administración - PROVICHECK",
    page_icon="⚙️",
    layout="wide",
)

aplicar_estilo()
encabezado()

st.title("⚙️ Administración")
st.caption("Consulta de la base de datos operativa SQLite")

tab1, tab2, tab3 = st.tabs(
    [
        "📋 Sesiones",
        "🔎 Detalle",
        "📘 Bitácora",
    ]
)

# ==========================================================
# SESIONES
# ==========================================================

with tab1:

    st.subheader("Últimas sesiones registradas")

    sesiones = consultar_sesiones_verificacion()

    if sesiones.empty:
        st.info("Todavía no existen sesiones registradas.")
    else:
        st.dataframe(
            sesiones,
            use_container_width=True,
            hide_index=True,
        )

# ==========================================================
# DETALLE
# ==========================================================

with tab2:

    st.subheader("Detalle de una sesión")

    sesiones = consultar_sesiones_verificacion()

    if sesiones.empty:

        st.info("No existen sesiones.")

    else:

        id_sesion = st.selectbox(
            "Seleccione la sesión",
            sesiones["id_sesion"].tolist(),
        )

        detalle = consultar_detalle_sesion(id_sesion)

        st.dataframe(
            detalle,
            use_container_width=True,
            hide_index=True,
        )

# ==========================================================
# BITÁCORA
# ==========================================================

with tab3:

    st.subheader("Bitácora")

    codigo = st.text_input(
        "Filtrar por equipo (opcional)",
        "",
    )

    if codigo == "":
        bitacora = consultar_bitacora_equipo()
    else:
        bitacora = consultar_bitacora_equipo(codigo)

    if bitacora.empty:
        st.info("No existen registros en la bitácora.")
    else:
        st.dataframe(
            bitacora,
            use_container_width=True,
            hide_index=True,
        )