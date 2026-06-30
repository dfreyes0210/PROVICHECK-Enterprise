import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.ui import aplicar_estilo, encabezado
from utils.data import cargar_hoja

st.set_page_config(
    page_title="Hoja de Vida Enterprise - PROVICHECK",
    page_icon="📘",
    layout="wide"
)

aplicar_estilo()
encabezado()

equipo = st.session_state.get("equipo_seleccionado")

if not equipo:
    st.warning("Seleccione primero un equipo desde el módulo Equipos.")
    st.page_link("pages/01_Equipos.py", label="🧪 Ir a Equipos")
    st.stop()

codigo = equipo.get("codigo_equipo", "Sin código")
nombre = equipo.get("nombre_equipo", "Equipo sin nombre")
estado = equipo.get("estado", "Sin estado")
criticidad = equipo.get("criticidad", "Sin criticidad")
laboratorio = equipo.get("laboratorio", "Sin laboratorio")
ubicacion = equipo.get("ubicacion", "Sin ubicación")
responsable = equipo.get("responsable", "Sin responsable")
marca = equipo.get("marca", "Sin marca")
modelo = equipo.get("modelo", "Sin modelo")
serie = equipo.get("serie", "Sin serie")
frecuencia = equipo.get("frecuencia_verificacion", "Sin frecuencia")

st.title("📘 Hoja de Vida Enterprise")
st.subheader(f"{codigo} · {nombre}")

st.divider()

col_foto, col_info, col_estado = st.columns([1, 2, 1])

with col_foto:
    st.info("📷 Foto del equipo")
    st.info("🔳 Código QR")

with col_info:
    st.markdown("### Identidad del equipo")
    st.write(f"**Código:** {codigo}")
    st.write(f"**Nombre:** {nombre}")
    st.write(f"**Marca:** {marca}")
    st.write(f"**Modelo:** {modelo}")
    st.write(f"**Serie:** {serie}")
    st.write(f"**Laboratorio:** {laboratorio}")
    st.write(f"**Ubicación:** {ubicacion}")
    st.write(f"**Responsable:** {responsable}")

with col_estado:
    st.metric("Estado", estado)
    st.metric("Criticidad", criticidad)
    st.metric("Frecuencia", frecuencia)

st.divider()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Verificaciones", "Pendiente")
m2.metric("Documentos", "Pendiente")
m3.metric("Calibraciones", "Pendiente")
m4.metric("Alertas", "0")

tabs = st.tabs([
    "📋 Información",
    "✅ Verificaciones",
    "📈 Tendencias",
    "📂 Documentos",
    "📜 Calibraciones",
    "🛠️ Mantenimientos",
    "📝 Bitácora",
    "🔍 Auditoría",
    "📊 Indicadores"
])

with tabs[0]:
    st.markdown("### Información técnica completa")
    df_info = pd.DataFrame([equipo]).T
    df_info.columns = ["Valor"]
    st.dataframe(df_info, use_container_width=True)

with tabs[1]:
    st.markdown("### Historial de verificaciones")
    verificaciones = cargar_hoja("Verificaciones")

    if verificaciones.empty:
        st.info("Aún no hay verificaciones registradas para este equipo.")
    else:
        st.dataframe(verificaciones.head(100), use_container_width=True)

with tabs[2]:
    st.markdown("### Tendencia por punto de inspección")

    punto = st.selectbox(
        "Seleccione punto de inspección",
        [
            "Peso patrón 100 g",
            "Peso patrón 200 g",
            "Peso patrón 500 g",
            "Nivelación",
            "Limpieza",
            "Estado general"
        ]
    )

    fechas = pd.date_range("2026-06-01", periods=10, freq="D")
    valores = [
        200.0000,
        200.0001,
        199.9999,
        200.0000,
        200.0001,
        200.0002,
        200.0000,
        199.9999,
        200.0001,
        200.0000
    ]

    patron = 200.0000
    li = 199.9998
    ls = 200.0002

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fechas,
        y=valores,
        mode="lines+markers",
        name="Valor medido"
    ))
    fig.add_trace(go.Scatter(
        x=fechas,
        y=[patron] * len(fechas),
        mode="lines",
        name="Valor patrón"
    ))
    fig.add_trace(go.Scatter(
        x=fechas,
        y=[ls] * len(fechas),
        mode="lines",
        name="Límite superior"
    ))
    fig.add_trace(go.Scatter(
        x=fechas,
        y=[li] * len(fechas),
        mode="lines",
        name="Límite inferior"
    ))

    fig.update_layout(
        height=480,
        title=f"Tendencia histórica - {punto}",
        xaxis_title="Fecha",
        yaxis_title="Resultado",
        legend_title="Serie"
    )

    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor patrón", patron)
    c2.metric("Límite inferior", li)
    c3.metric("Límite superior", ls)
    c4.metric("Estado", "🟢 Estable")

with tabs[3]:
    st.markdown("### Biblioteca documental")
    st.info("Aquí se consultarán documentos asociados al equipo.")
    st.write("- Certificados de calibración")
    st.write("- Manuales")
    st.write("- Fotografías")
    st.write("- Procedimientos")
    st.write("- Evidencias de auditoría")

with tabs[4]:
    st.markdown("### Calibraciones externas")
    st.info("Consulta rápida de certificados de calibración externa.")
    st.table({
        "Fecha": ["Pendiente"],
        "Documento": ["Certificado externo"],
        "Estado": ["Disponible próximamente"]
    })

with tabs[5]:
    st.markdown("### Mantenimientos")
    st.info("Historial de mantenimientos preventivos y correctivos.")

with tabs[6]:
    st.markdown("### Bitácora del equipo")
    st.info("Eventos importantes durante el ciclo de vida del equipo.")

with tabs[7]:
    st.markdown("### Auditoría")
    st.info("Registro de cambios: usuario, fecha, campo modificado, valor anterior y valor nuevo.")

with tabs[8]:
    st.markdown("### Indicadores del equipo")

    i1, i2, i3 = st.columns(3)
    i1.metric("Disponibilidad", "100 %")
    i2.metric("Cumplimiento", "Pendiente")
    i3.metric("Condición", "🟢 Normal")