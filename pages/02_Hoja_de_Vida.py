import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.ui import aplicar_estilo, encabezado
from utils.data import cargar_hoja

st.set_page_config(page_title="Hoja de Vida - PROVICHECK", page_icon="📘", layout="wide")
aplicar_estilo(); encabezado()
equipo = st.session_state.get("equipo_seleccionado")
if not equipo:
    st.warning("Seleccione un equipo desde el módulo Equipos.")
    st.stop()

codigo = equipo.get("codigo_equipo", "Sin código")
nombre = equipo.get("nombre_equipo", "Equipo")
st.title("📘 Hoja de Vida Digital")
st.subheader(f"{codigo} · {nombre}")

tabs = st.tabs(["Información", "Verificaciones", "Tendencias", "Documentos", "Calibraciones", "Bitácora", "Auditoría", "Indicadores"])
with tabs[0]:
    st.markdown("### Información general")
    col1, col2 = st.columns(2)
    with col1:
        for k, v in equipo.items():
            st.write(f"**{k}:** {v}")
    with col2:
        st.info("Aquí irá la fotografía del equipo y el código QR.")
with tabs[1]:
    st.markdown("### Verificaciones históricas")
    verificaciones = cargar_hoja("Verificaciones")
    if verificaciones.empty: st.info("No hay verificaciones cargadas todavía.")
    else: st.dataframe(verificaciones.head(50), use_container_width=True)
with tabs[2]:
    st.markdown("### Tendencia inicial por punto de inspección")
    st.info("Gráfica demostrativa. La siguiente etapa la conectará a los resultados reales por punto de inspección.")
    fechas = pd.date_range("2026-06-01", periods=8, freq="D")
    valores = [200.0000, 200.0001, 199.9999, 200.0000, 200.0001, 200.0002, 200.0000, 199.9999]
    patron, li, ls = 200.0000, 199.9998, 200.0002
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fechas, y=valores, mode="lines+markers", name="Valor medido"))
    fig.add_trace(go.Scatter(x=fechas, y=[patron]*len(fechas), mode="lines", name="Valor patrón"))
    fig.add_trace(go.Scatter(x=fechas, y=[ls]*len(fechas), mode="lines", name="Límite superior"))
    fig.add_trace(go.Scatter(x=fechas, y=[li]*len(fechas), mode="lines", name="Límite inferior"))
    fig.update_layout(height=450, title="Ejemplo: Peso patrón 200 g", xaxis_title="Fecha", yaxis_title="g")
    st.plotly_chart(fig, use_container_width=True)
with tabs[3]: st.info("Biblioteca documental: certificados, manuales, mantenimientos, fotografías y calibraciones externas.")
with tabs[4]: st.info("Consulta de certificados externos asociados al equipo.")
with tabs[5]: st.info("Historial técnico del equipo.")
with tabs[6]: st.info("Registro de cambios, usuario, fecha y detalle de modificación.")
with tabs[7]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Estado", equipo.get("estado", "Sin estado"))
    c2.metric("Criticidad", equipo.get("criticidad", "Sin criticidad"))
    c3.metric("Verificación", equipo.get("frecuencia_verificacion", "Sin frecuencia"))
