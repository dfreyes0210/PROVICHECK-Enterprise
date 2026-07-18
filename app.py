import pandas as pd
import streamlit as st
import plotly.express as px

from config import APP_NAME, VERSION
from database import crear_base_datos
from utils.ui import aplicar_estilo, encabezado, login_limpio, pie_pagina
from utils.dashboard import (
    obtener_kpis,
    obtener_estado_verificaciones,
    obtener_equipos_por_laboratorio,
    obtener_ultimas_verificaciones,
    obtener_bitacora_reciente,
    obtener_alertas,
    obtener_proximas_verificaciones,
    obtener_estado_general,
    obtener_resumen_programacion,
    obtener_indice_salud,
    obtener_agenda_critica,
    obtener_tendencia_mensual,
    obtener_ranking_equipos,
)


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

    col_izquierda, col_login, col_derecha = st.columns([1, 1.15, 1])

    with col_login:
        login_limpio()

    st.stop()


with st.sidebar:
    st.title("PROVICHECK")
    st.caption(f"Enterprise · {VERSION}")
    st.write(f"Usuario: **{st.session_state.get('usuario', '')}**")

    st.divider()

    st.page_link("app.py", label="🏠 Dashboard")
    st.page_link("pages/01_Equipos.py", label="🧪 Equipos")
    st.page_link("pages/02_Hoja_de_Vida.py", label="📘 Hoja de Vida")
    st.page_link("pages/03_Administracion.py", label="⚙️ Administración")
    st.page_link("pages/04_Verificaciones.py", label="✅ Verificaciones")

    st.divider()

    if st.button("Cerrar sesión", width="stretch"):
        st.session_state["autenticado"] = False
        st.rerun()


encabezado()

kpis = obtener_kpis()
estado_verificaciones = obtener_estado_verificaciones()
equipos_laboratorio = obtener_equipos_por_laboratorio()
ultimas_verificaciones = obtener_ultimas_verificaciones(8)
actividad_reciente = obtener_bitacora_reciente(8)
alertas = obtener_alertas(5)
proximas_verificaciones = obtener_proximas_verificaciones()
estado_general = obtener_estado_general()
resumen_programacion = obtener_resumen_programacion()
indice_salud = obtener_indice_salud()
agenda_critica = obtener_agenda_critica(10)
tendencia_mensual = obtener_tendencia_mensual()
ranking_equipos = obtener_ranking_equipos(8)


st.subheader("Centro de control")

col_salud, col_estado = st.columns([1, 1.7])

with col_salud:
    with st.container(border=True):
        st.markdown("### 🧪 Salud del laboratorio")
        st.metric(
            "Índice general",
            f'{indice_salud["indice"]:.1f} %',
            delta=f'{indice_salud["estado"]} {indice_salud["nivel"]}',
        )
        st.progress(indice_salud["indice"] / 100)

with col_estado:
    if estado_general["nivel"] == "error":
        st.error(
            f'### {estado_general["estado"]}\n\n'
            f'{estado_general["detalle"]}'
        )
    elif estado_general["nivel"] == "warning":
        st.warning(
            f'### {estado_general["estado"]}\n\n'
            f'{estado_general["detalle"]}'
        )
    else:
        st.success(
            f'### {estado_general["estado"]}\n\n'
            f'{estado_general["detalle"]}'
        )

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Equipos registrados",
    kpis["equipos"],
    delta=f'{kpis["activos"]} activos',
)

c2.metric(
    "Verificaciones",
    kpis["verificaciones"],
    delta=f'{kpis["conformes"]} conformes',
)

c3.metric(
    "Conformidad",
    f'{kpis["porcentaje_conformidad"]:.1f} %',
)

c4.metric(
    "Alertas",
    kpis["alertas"],
    delta=(
        f'{kpis["no_conformes"]} no conformes · '
        f'{kpis["incompletas"]} incompletas'
    ),
    delta_color="inverse",
)

st.markdown("### Semáforo de programación")
s1, s2, s3, s4, s5 = st.columns(5)

s1.metric("🟢 Vigentes", resumen_programacion["vigentes"])
s2.metric("🟡 Próximas", resumen_programacion["proximas"])
s3.metric("🔴 Vencidas", resumen_programacion["vencidas"])
s4.metric("🔴 Sin verificar", resumen_programacion["sin_verificar"])
s5.metric("⚪ Sin frecuencia", resumen_programacion["sin_frecuencia"])

st.divider()

col_grafico_1, col_grafico_2 = st.columns([1, 1.25])

with col_grafico_1:
    st.markdown("### Estado de verificaciones")

    if estado_verificaciones.empty:
        st.info("Aún no hay verificaciones registradas.")
    else:
        fig_estado = px.pie(
            estado_verificaciones,
            names="estado",
            values="cantidad",
            hole=0.58,
            color="estado",
            color_discrete_map={
                "Conforme": "#1F7A3E",
                "No conforme": "#C62828",
                "Incompleta": "#D97706",
            },
        )
        fig_estado.update_traces(
            textposition="inside",
            textinfo="percent+label",
        )
        fig_estado.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
        )
        st.plotly_chart(fig_estado, width="stretch")

with col_grafico_2:
    st.markdown("### Equipos por laboratorio")

    if equipos_laboratorio.empty:
        st.info("No hay información de laboratorios.")
    else:
        fig_laboratorios = px.bar(
            equipos_laboratorio,
            x="laboratorio",
            y="cantidad",
            text="cantidad",
        )
        fig_laboratorios.update_traces(
            marker_color="#005AA7",
            textposition="outside",
        )
        fig_laboratorios.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Laboratorio",
            yaxis_title="Equipos",
            showlegend=False,
        )
        st.plotly_chart(fig_laboratorios, width="stretch")

st.divider()

col_tendencia, col_agenda = st.columns([1.2, 1])

with col_tendencia:
    st.markdown("### Tendencia mensual")

    if tendencia_mensual.empty:
        st.info("Aún no hay información mensual suficiente.")
    else:
        fig_tendencia = px.line(
            tendencia_mensual,
            x="mes",
            y="verificaciones",
            markers=True,
        )
        fig_tendencia.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Mes",
            yaxis_title="Verificaciones",
            showlegend=False,
        )
        st.plotly_chart(fig_tendencia, width="stretch")

with col_agenda:
    st.markdown("### Agenda crítica")

    if agenda_critica.empty:
        st.success("No hay verificaciones críticas pendientes.")
    else:
        st.dataframe(
            agenda_critica,
            width="stretch",
            hide_index=True,
        )

st.divider()

col_verificaciones, col_alertas = st.columns([1.55, 1])

with col_verificaciones:
    st.markdown("### Últimas verificaciones")

    if ultimas_verificaciones.empty:
        st.info("Aún no existen sesiones registradas.")
    else:
        columnas_visibles = [
            columna
            for columna in [
                "fecha",
                "hora",
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "responsable",
                "estado",
                "total_puntos",
            ]
            if columna in ultimas_verificaciones.columns
        ]

        st.dataframe(
            ultimas_verificaciones[columnas_visibles],
            width="stretch",
            hide_index=True,
        )

with col_alertas:
    st.markdown("### Alertas y atención")

    if not alertas:
        st.success("No existen alertas operativas.")
    else:
        for alerta in alertas:
            texto = f'**{alerta["titulo"]}**\n\n{alerta["detalle"]}'

            if alerta["nivel"] == "error":
                st.error(texto)
            elif alerta["nivel"] == "warning":
                st.warning(texto)
            else:
                st.info(texto)

st.divider()

st.markdown("### Equipos con mayor actividad")

if ranking_equipos.empty:
    st.info("Aún no hay información para construir el ranking.")
else:
    fig_ranking = px.bar(
        ranking_equipos.sort_values("verificaciones"),
        x="verificaciones",
        y="codigo_equipo",
        orientation="h",
        text="verificaciones",
        hover_data=[
            columna
            for columna in ["nombre_equipo", "laboratorio"]
            if columna in ranking_equipos.columns
        ],
    )
    fig_ranking.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Verificaciones",
        yaxis_title="Equipo",
        showlegend=False,
    )
    st.plotly_chart(fig_ranking, width="stretch")

st.divider()

st.markdown("### Actividad reciente")

if actividad_reciente.empty:
    st.info("La bitácora todavía no tiene eventos.")
else:
    columnas_bitacora = [
        columna
        for columna in [
            "fecha",
            "hora",
            "codigo_equipo",
            "evento",
            "detalle",
            "usuario",
            "origen",
        ]
        if columna in actividad_reciente.columns
    ]

    st.dataframe(
        actividad_reciente[columnas_bitacora],
        width="stretch",
        hide_index=True,
    )

pie_pagina()