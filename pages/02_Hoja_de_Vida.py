import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.ui import aplicar_estilo, encabezado
from utils.formatos import formatear_numero
from utils.sqlite_consultas import (
    consultar_ultima_verificacion,
    consultar_historial_equipo,
    consultar_eventos_equipo,
    consultar_detalle_sesion,
)


st.set_page_config(
    page_title="Hoja de Vida Enterprise - PROVICHECK",
    page_icon="📘",
    layout="wide",
)

aplicar_estilo()
encabezado()


def estado_visual(estado):
    estado_txt = str(estado).lower()

    if "conforme" in estado_txt and "no" not in estado_txt:
        return "🟢 Conforme"

    if "no conforme" in estado_txt:
        return "🔴 No conforme"

    if "incompleta" in estado_txt:
        return "🟡 Incompleta"

    if "cumple" in estado_txt:
        return "🟢 Cumple"

    if "no cumple" in estado_txt:
        return "🔴 No cumple"

    return f"⚪ {estado}"


equipo = st.session_state.get("equipo_seleccionado")

if not equipo:
    st.warning("Seleccione primero un equipo desde el módulo Equipos.")
    st.page_link("pages/01_Equipos.py", label="🧪 Ir a Equipos")
    st.stop()

codigo = str(equipo.get("codigo_equipo", "Sin código"))
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

ultima = consultar_ultima_verificacion(codigo)
historial = consultar_historial_equipo(codigo, limite=20)
eventos = consultar_eventos_equipo(codigo, limite=20)

st.title("📘 Hoja de Vida del Equipo")
st.subheader(f"{codigo} · {nombre}")

st.divider()

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    with st.container(border=True):
        st.markdown("### 📷 Equipo")
        st.info("Fotografía pendiente")
        st.info("Código QR pendiente")

with col2:
    with st.container(border=True):
        st.markdown("### Identidad técnica")
        st.write(f"**Código:** {codigo}")
        st.write(f"**Nombre:** {nombre}")
        st.write(f"**Marca:** {marca}")
        st.write(f"**Modelo:** {modelo}")
        st.write(f"**Serie:** {serie}")
        st.write(f"**Laboratorio:** {laboratorio}")
        st.write(f"**Ubicación:** {ubicacion}")
        st.write(f"**Responsable:** {responsable}")

with col3:
    with st.container(border=True):
        st.markdown("### Estado")
        st.metric("Estado", estado)
        st.metric("Criticidad", criticidad)
        st.metric("Frecuencia", frecuencia)

st.divider()

if not ultima.empty:
    ultima_fila = ultima.iloc[0]
    ultima_fecha = ultima_fila.get("fecha", "Sin fecha")
    ultima_estado = ultima_fila.get("estado", "Sin estado")
    total_verificaciones = len(historial)
    total_eventos = len(eventos)
else:
    ultima_fila = None
    ultima_fecha = "Sin registros"
    ultima_estado = "Sin registros"
    total_verificaciones = 0
    total_eventos = 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Última verificación", ultima_fecha)
k2.metric("Estado última sesión", estado_visual(ultima_estado))
k3.metric("Sesiones registradas", total_verificaciones)
k4.metric("Eventos en bitácora", total_eventos)

tabs = st.tabs(
    [
        "📋 Información",
        "✅ Última verificación",
        "📜 Historial",
        "📝 Bitácora",
        "📈 Tendencias",
        "📂 Documentos",
        "🔍 Auditoría",
    ]
)

with tabs[0]:
    st.markdown("### Información técnica completa")
    df_info = pd.DataFrame([equipo]).T
    df_info.columns = ["Valor"]
    st.dataframe(df_info, width="stretch")

with tabs[1]:
    st.markdown("### Última verificación registrada")

    if ultima.empty:
        st.info("Este equipo aún no tiene verificaciones guardadas en SQLite.")
    else:
        col_a, col_b, col_c, col_d = st.columns(4)

        col_a.metric("Fecha", ultima_fila.get("fecha", ""))
        col_b.metric("Hora", ultima_fila.get("hora", ""))
        col_c.metric("Responsable", ultima_fila.get("responsable", ""))
        col_d.metric("Estado", estado_visual(ultima_fila.get("estado", "")))

        st.divider()

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Puntos", int(ultima_fila.get("total_puntos", 0)))
        r2.metric("Cumplen", int(ultima_fila.get("puntos_cumplen", 0)))
        r3.metric("No cumplen", int(ultima_fila.get("puntos_no_cumplen", 0)))
        r4.metric("No evaluados", int(ultima_fila.get("puntos_no_evaluados", 0)))

        detalle = consultar_detalle_sesion(ultima_fila.get("id_sesion"))

        st.markdown("### Detalle de la última sesión")
        if detalle.empty:
            st.info("No se encontró detalle para esta sesión.")
        else:
            st.dataframe(detalle, width="stretch", hide_index=True)

with tabs[2]:
    st.markdown("### Historial de verificaciones")

    if historial.empty:
        st.info("No hay historial registrado para este equipo.")
    else:
        st.dataframe(historial, width="stretch", hide_index=True)

        id_sesion = st.selectbox(
            "Ver detalle de sesión",
            historial["id_sesion"].tolist(),
        )

        detalle_hist = consultar_detalle_sesion(id_sesion)

        st.markdown("### Detalle seleccionado")
        st.dataframe(detalle_hist, width="stretch", hide_index=True)

with tabs[3]:
    st.markdown("### Bitácora del equipo")

    if eventos.empty:
        st.info("No hay eventos registrados en la bitácora para este equipo.")
    else:
        st.dataframe(eventos, width="stretch", hide_index=True)

with tabs[4]:
    st.markdown("### Tendencia por punto de verificación")

    if historial.empty:
        st.info("Aún no hay datos suficientes para construir tendencias.")
    else:
        detalles = []

        for id_sesion in historial["id_sesion"].tolist():
            df_detalle = consultar_detalle_sesion(id_sesion)

            if not df_detalle.empty:
                df_detalle = df_detalle.copy()
                df_detalle["id_sesion"] = id_sesion

                fila_sesion = historial[historial["id_sesion"] == id_sesion].iloc[0]
                df_detalle["fecha"] = fila_sesion.get("fecha")
                df_detalle["hora"] = fila_sesion.get("hora")

                detalles.append(df_detalle)

        if not detalles:
            st.info("No hay detalle suficiente para graficar tendencias.")
        else:
            df_tendencia = pd.concat(detalles, ignore_index=True)

            puntos_disponibles = (
                df_tendencia["punto"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            punto_sel = st.selectbox(
                "Seleccione punto",
                puntos_disponibles,
            )

            df_punto = df_tendencia[
                df_tendencia["punto"].astype(str) == str(punto_sel)
            ].copy()

            df_punto["fecha_hora"] = pd.to_datetime(
                df_punto["fecha"].astype(str) + " " + df_punto["hora"].astype(str),
                errors="coerce",
            )

            df_punto = df_punto.sort_values("fecha_hora")

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=df_punto["fecha_hora"],
                    y=df_punto["resultado"],
                    mode="lines+markers",
                    name="Resultado observado",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=df_punto["fecha_hora"],
                    y=df_punto["valor_nominal"],
                    mode="lines",
                    name="Valor nominal",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=df_punto["fecha_hora"],
                    y=df_punto["limite_superior"],
                    mode="lines",
                    name="Límite superior",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=df_punto["fecha_hora"],
                    y=df_punto["limite_inferior"],
                    mode="lines",
                    name="Límite inferior",
                )
            )

            fig.update_layout(
                height=480,
                title=f"Tendencia histórica - {punto_sel}",
                xaxis_title="Fecha",
                yaxis_title="Resultado",
                legend_title="Serie",
            )

            st.plotly_chart(fig, width="stretch")

            st.markdown("### Datos usados para la tendencia")
            st.dataframe(
                df_punto[
                    [
                        "fecha",
                        "hora",
                        "punto",
                        "valor_nominal",
                        "resultado",
                        "error",
                        "limite_inferior",
                        "limite_superior",
                        "estado_punto",
                        "observacion",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )

with tabs[5]:
    st.markdown("### Biblioteca documental")
    st.info("Aquí se consultarán certificados, manuales, procedimientos y evidencias del equipo.")

with tabs[6]:
    st.markdown("### Auditoría")
    st.info("Aquí se mostrará el historial de cambios y trazabilidad del equipo.")