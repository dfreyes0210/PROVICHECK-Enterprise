import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import crear_base_datos

from utils.ui import aplicar_estilo, encabezado
from utils.formatos import formatear_numero
from utils.documentos import (
    actualizar_estados_documentos,
    eliminar_documento,
    leer_documento,
    registrar_documento,
)
from utils.sqlite_consultas import (
    consultar_ultima_verificacion,
    consultar_historial_equipo,
    consultar_eventos_equipo,
    consultar_detalle_sesion,
    consultar_documentos_equipo,
)


st.set_page_config(
    page_title="Hoja de Vida Enterprise - PROVICHECK",
    page_icon="📘",
    layout="wide",
)

crear_base_datos()

aplicar_estilo()
encabezado()


st.markdown(
    """
    <style>
    /* Etiquetas de los controles del formulario documental */
    div[data-testid="stTextInput"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stFileUploader"] label,
    div[data-testid="stCheckbox"] label {
        color: #1f2937 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* Texto auxiliar y descripción del cargador */
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] p {
        color: #374151 !important;
        opacity: 1 !important;
    }

    /* Texto visible del checkbox */
    div[data-testid="stCheckbox"] p,
    div[data-testid="stCheckbox"] span {
        color: #1f2937 !important;
        opacity: 1 !important;
    }

    /* Encabezado del expander oscuro */
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {
        color: #ffffff !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* Texto dentro de campos oscuros */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stDateInput"] input {
        color: #ffffff !important;
        opacity: 1 !important;
    }

    /* Texto seleccionado en listas */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
        color: #ffffff !important;
        opacity: 1 !important;
    }

    /* Placeholder de entradas */
    input::placeholder,
    textarea::placeholder {
        color: #d1d5db !important;
        opacity: 1 !important;
    }

    /* Títulos y textos generales del área documental */
    div[data-testid="stForm"] p,
    div[data-testid="stForm"] label {
        opacity: 1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



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
actualizar_estados_documentos(codigo)
documentos = consultar_documentos_equipo(codigo)

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

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Última verificación", ultima_fecha)
k2.metric("Estado última sesión", estado_visual(ultima_estado))
k3.metric("Sesiones registradas", total_verificaciones)
k4.metric("Eventos en bitácora", total_eventos)
k5.metric("Documentos", len(documentos))

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
    st.caption("Carga, consulta y descarga de documentos asociados al equipo.")

    with st.expander("➕ Cargar nuevo documento", expanded=documentos.empty):
        with st.form(f"form_documento_{codigo}", clear_on_submit=True):
            d1, d2 = st.columns(2)
            with d1:
                tipo_documento = st.selectbox("Tipo de documento *", ["Certificado de calibración","Certificado de verificación","Manual","Procedimiento","Ficha técnica","Fotografía","Mantenimiento","Calificación","Otro"])
                titulo_documento = st.text_input("Título", placeholder="Ej.: Certificado de calibración 2026")
                archivo_documento = st.file_uploader("Seleccionar archivo *", type=["pdf","png","jpg","jpeg","webp","doc","docx","xls","xlsx","csv","txt"])
                responsable_documento = st.text_input("Responsable", value=str(st.session_state.get("usuario", "")))
            with d2:
                fecha_emision_documento = st.date_input("Fecha de emisión", value=None)
                tiene_vencimiento = st.checkbox("Tiene fecha de vencimiento")
                fecha_vencimiento_documento = st.date_input("Fecha de vencimiento") if tiene_vencimiento else None
                proveedor_documento = st.text_input("Proveedor o emisor")
                version_documento = st.text_input("Versión")
                observaciones_documento = st.text_area("Observaciones")
            guardar_documento = st.form_submit_button("💾 Guardar documento", type="primary", width="stretch")

        if guardar_documento:
            if archivo_documento is None:
                st.error("Debe seleccionar un archivo.")
            elif tiene_vencimiento and fecha_emision_documento and fecha_vencimiento_documento < fecha_emision_documento:
                st.error("La fecha de vencimiento no puede ser anterior a la fecha de emisión.")
            else:
                try:
                    registrar_documento(codigo, tipo_documento, archivo_documento, titulo_documento, fecha_emision_documento, fecha_vencimiento_documento, responsable_documento, proveedor_documento, version_documento, observaciones_documento)
                    st.success("Documento cargado correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible guardar el documento: {exc}")

    documentos = consultar_documentos_equipo(codigo)
    if documentos.empty:
        st.info("Este equipo aún no tiene documentos registrados.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(documentos))
        m2.metric("🟢 Vigentes", int((documentos["estado"] == "Vigente").sum()))
        m3.metric("🟡 Próximos", int((documentos["estado"] == "Próximo a vencer").sum()))
        m4.metric("🔴 Vencidos", int((documentos["estado"] == "Vencido").sum()))
        for _, documento in documentos.iterrows():
            estado_doc = str(documento.get("estado", "Sin estado"))
            icono = {"Vigente":"🟢","Próximo a vencer":"🟡","Vencido":"🔴","Sin vencimiento":"⚪"}.get(estado_doc,"⚪")
            with st.container(border=True):
                c_info, c_acciones = st.columns([3,1])
                with c_info:
                    st.markdown(f"#### {icono} {documento.get('titulo') or documento.get('nombre_archivo')}")
                    st.write(f"**Tipo:** {documento.get('tipo_documento','')}")
                    st.write(f"**Archivo:** {documento.get('nombre_archivo','')}")
                    if documento.get('fecha_vencimiento'):
                        st.caption(f"Vence: {documento.get('fecha_vencimiento')}")
                    if documento.get('observaciones'):
                        st.write(f"**Observaciones:** {documento.get('observaciones')}")
                with c_acciones:
                    st.metric("Estado", estado_doc)
                    try:
                        st.download_button("⬇️ Descargar", data=leer_documento(documento.get('ruta_archivo')), file_name=documento.get('nombre_archivo'), mime=documento.get('mime_type') or 'application/octet-stream', key=f"descargar_doc_{documento.get('id')}", width="stretch")
                    except FileNotFoundError:
                        st.error("Archivo no disponible.")
                    confirmar = st.checkbox("Confirmar eliminación", key=f"confirmar_doc_{documento.get('id')}")
                    if st.button("🗑️ Eliminar", key=f"eliminar_doc_{documento.get('id')}", disabled=not confirmar, width="stretch"):
                        eliminar_documento(documento.get('id'))
                        st.success("Documento eliminado.")
                        st.rerun()

with tabs[6]:
    st.markdown("### Auditoría")
    st.info("Aquí se mostrará el historial de cambios y trazabilidad del equipo.")