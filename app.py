import streamlit as st
import plotly.express as px

from config import APP_NAME
from database import crear_base_datos
from utils.data import cargar_hoja
from utils.ui import (
    aplicar_estilo,
    encabezado,
    login_limpio,
    pie_pagina,
    sidebar_pro,
)
from utils.dashboard import (
    obtener_acciones_inmediatas,
    obtener_alertas,
    obtener_bitacora_reciente,
    obtener_cumplimiento_laboratorios,
    obtener_equipos_cumplidos_periodo,
    obtener_equipos_pendientes_periodo,
    obtener_estado_general,
    obtener_indice_salud,
    obtener_kpis,
    obtener_patrones_alerta,
    obtener_resumen_programacion,
    obtener_ultimas_verificaciones,
    obtener_verificaciones_atencion,
)


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilo()
crear_base_datos()

st.markdown(
    """
    <style>
    .pc-exec-title{
        font-size:22px;
        font-weight:800;
        line-height:1.2;
        color:#0f2747;
        margin-bottom:.18rem;
    }

    .pc-exec-sub{
        font-size:12px;
        line-height:1.35;
        color:#5f718a;
        margin-bottom:.75rem;
    }

    .pc-section-title{
        font-size:16px;
        font-weight:800;
        color:#0f2747;
        margin:.15rem 0 .45rem 0;
    }

    .pc-action{
        border:1px solid #d5e1f0;
        border-left:4px solid #147a3b;
        border-radius:10px;
        background:#fff;
        padding:.58rem .68rem;
        margin-bottom:.42rem;
    }

    .pc-action.red{border-left-color:#c62828;}
    .pc-action.yellow{border-left-color:#d99a00;}

    .pc-action-title{
        font-size:12px;
        line-height:1.25;
        font-weight:800;
        color:#0f2747;
        overflow-wrap:anywhere;
    }

    .pc-action-detail{
        font-size:10px;
        line-height:1.35;
        color:#5f718a;
        margin-top:.15rem;
        overflow-wrap:anywhere;
    }

    div[data-testid="stMetric"]{
        min-height:72px!important;
        padding:.52rem .62rem!important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *{
        font-size:10px!important;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *{
        font-size:17px!important;
        line-height:1.1!important;
        white-space:normal!important;
        overflow:visible!important;
        text-overflow:clip!important;
    }

    div[data-testid="stMetricDelta"],
    div[data-testid="stMetricDelta"] *{
        font-size:9px!important;
    }

    .block-container h3{
        font-size:16px!important;
        line-height:1.2!important;
    }

    button[data-baseweb="tab"]{
        padding:.30rem .45rem!important;
        min-height:32px!important;
    }

    button[data-baseweb="tab"] *,
    button[data-baseweb="tab"] p{
        font-size:10px!important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    encabezado()
    _, col_login, _ = st.columns([1, 1.15, 1])
    with col_login:
        login_limpio()
    st.stop()

sidebar_pro()
encabezado()


def normalizar_codigo(valor):
    texto = str(valor or "").strip()
    if (
        texto.endswith(".0")
        and texto[:-2].replace("-", "").isdigit()
    ):
        return texto[:-2]
    return texto


def abrir_equipo(codigo):
    equipos = cargar_hoja("Equipos")

    if equipos.empty or "codigo_equipo" not in equipos.columns:
        st.error("No fue posible cargar el catálogo de equipos.")
        return

    equipos = equipos.copy()
    equipos["_codigo"] = equipos["codigo_equipo"].apply(
        normalizar_codigo
    )

    fila = equipos[
        equipos["_codigo"].eq(normalizar_codigo(codigo))
    ]

    if fila.empty:
        st.error(f"No se encontró el equipo {codigo}.")
        return

    st.session_state["equipo_seleccionado"] = (
        fila.iloc[0]
        .drop(labels=["_codigo"], errors="ignore")
        .to_dict()
    )
    st.switch_page("pages/02_Hoja_de_Vida.py")


# ---------------------------------------------------------------------
# DATOS EJECUTIVOS
# ---------------------------------------------------------------------

kpis = obtener_kpis()
resumen = obtener_resumen_programacion()
salud = obtener_indice_salud()
estado_general = obtener_estado_general()

acciones = obtener_acciones_inmediatas(8)
alertas = obtener_alertas(6)
patrones = obtener_patrones_alerta(30, 12)
no_conformes = obtener_verificaciones_atencion(12)

pendientes_periodo = obtener_equipos_pendientes_periodo(1000)
cumplidos_periodo = obtener_equipos_cumplidos_periodo(1000)
cumplimiento_laboratorios = obtener_cumplimiento_laboratorios()

ultimas = obtener_ultimas_verificaciones(8)
actividad = obtener_bitacora_reciente(8)


# ---------------------------------------------------------------------
# ENCABEZADO EJECUTIVO
# ---------------------------------------------------------------------

st.markdown(
    '<div class="pc-exec-title">Dashboard ejecutivo</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="pc-exec-sub">'
    'Estado del programa metrológico y situaciones que requieren decisión.'
    '</div>',
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Cumplimiento del programa",
    f'{resumen["porcentaje_cumplimiento"]:.1f} %',
    delta=(
        f'{resumen["cumplidos"]} de '
        f'{resumen["programados"]} equipos'
    ),
)

m2.metric(
    "Conformidad",
    f'{kpis["porcentaje_conformidad"]:.1f} %',
    delta=f'{kpis["no_conformes"]} no conformes',
    delta_color="inverse",
)

m3.metric(
    "Equipos activos",
    f'{kpis["activos"]} / {kpis["equipos"]}',
)

pendientes_total = (
    resumen["pendientes"]
    + resumen["sin_verificar"]
    + resumen["vencidos_intervalo"]
)

m4.metric(
    "Pendientes del período",
    pendientes_total,
    delta=f'{kpis["alertas"]} alertas',
    delta_color="inverse",
)

st.progress(
    min(
        max(
            resumen["porcentaje_cumplimiento"] / 100,
            0.0,
        ),
        1.0,
    )
)

st.divider()


# ---------------------------------------------------------------------
# ESTADO GENERAL + SALUD
# ---------------------------------------------------------------------

c_salud, c_estado = st.columns([1, 2])

with c_salud:
    with st.container(border=True):
        st.markdown(
            '<div class="pc-section-title">Salud operativa</div>',
            unsafe_allow_html=True,
        )
        st.metric(
            "Índice general",
            f'{salud["indice"]:.1f} %',
            delta=f'{salud["estado"]} {salud["nivel"]}',
        )
        st.progress(
            min(max(salud["indice"] / 100, 0.0), 1.0)
        )

with c_estado:
    mensaje = (
        f'**{estado_general["estado"]}**  \n'
        f'{estado_general["detalle"]}'
    )

    if estado_general["nivel"] == "error":
        st.error(mensaje)
    elif estado_general["nivel"] == "warning":
        st.warning(mensaje)
    else:
        st.success(mensaje)

st.divider()


# ---------------------------------------------------------------------
# ACCIONES INMEDIATAS
# ---------------------------------------------------------------------

st.markdown(
    '<div class="pc-section-title">🚨 Acciones inmediatas</div>',
    unsafe_allow_html=True,
)

if acciones.empty:
    st.success("No existen acciones inmediatas pendientes.")
else:
    col_acciones, col_abrir = st.columns([4, 1])

    with col_acciones:
        for _, fila in acciones.head(6).iterrows():
            nivel = str(fila.get("nivel", ""))
            clase = "red" if "🔴" in nivel else "yellow"

            codigo = str(
                fila.get("codigo_equipo", "") or ""
            ).strip()
            nombre = str(
                fila.get("nombre_equipo", "") or ""
            ).strip()
            motivo = str(
                fila.get("motivo", "") or ""
            ).strip()
            detalle = str(
                fila.get("detalle", "") or ""
            ).strip()

            titulo = (
                f"{nivel} {codigo}"
                + (f" · {nombre}" if nombre else "")
            )

            st.markdown(
                f"""
                <div class="pc-action {clase}">
                    <div class="pc-action-title">{titulo}</div>
                    <div class="pc-action-detail">
                        {motivo}<br>{detalle}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_abrir:
        codigos = (
            acciones["codigo_equipo"]
            .dropna()
            .astype(str)
        )
        codigos = codigos[
            codigos.str.strip().ne("")
            & codigos.str.lower().ne("equipo no relacionado")
        ].drop_duplicates().tolist()

        if codigos:
            equipo_accion = st.selectbox(
                "Abrir equipo",
                codigos,
                key="dash_exec_equipo",
            )
            if st.button(
                "📘 Hoja de Vida",
                width="stretch",
                type="primary",
                key="dash_exec_abrir",
            ):
                abrir_equipo(equipo_accion)

st.divider()


# ---------------------------------------------------------------------
# CUMPLIMIENTO DEL PROGRAMA
# ---------------------------------------------------------------------

st.markdown(
    '<div class="pc-section-title">📅 Cumplimiento del programa</div>',
    unsafe_allow_html=True,
)

tab_lab, tab_pend, tab_ok = st.tabs(
    [
        "🏭 Por laboratorio",
        "⏳ Pendientes",
        "✅ Cumplidos",
    ]
)

with tab_lab:
    if cumplimiento_laboratorios.empty:
        st.info("No hay información suficiente por laboratorio.")
    else:
        tabla_lab = cumplimiento_laboratorios[
            [
                columna
                for columna in [
                    "laboratorio",
                    "programados",
                    "cumplidos",
                    "pendientes",
                    "porcentaje_cumplimiento",
                    "estado_laboratorio",
                ]
                if columna in cumplimiento_laboratorios.columns
            ]
        ].copy()

        st.dataframe(
            tabla_lab,
            width="stretch",
            hide_index=True,
            height=min(330, 38 + len(tabla_lab) * 35),
            column_config={
                "porcentaje_cumplimiento":
                    st.column_config.ProgressColumn(
                        "Cumplimiento",
                        min_value=0,
                        max_value=100,
                        format="%.1f %%",
                    )
            },
        )

with tab_pend:
    if pendientes_periodo.empty:
        st.success(
            "Todos los equipos programados cumplieron su período."
        )
    else:
        columnas = [
            columna
            for columna in [
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "frecuencia",
                "periodo",
                "estado_programacion",
            ]
            if columna in pendientes_periodo.columns
        ]

        st.dataframe(
            pendientes_periodo[columnas],
            width="stretch",
            hide_index=True,
            height=min(
                330,
                38 + len(pendientes_periodo) * 35,
            ),
        )

with tab_ok:
    if cumplidos_periodo.empty:
        st.info(
            "Todavía no hay equipos cumplidos en el período."
        )
    else:
        columnas = [
            columna
            for columna in [
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "frecuencia",
                "fecha_cumplimiento",
                "responsable_cumplimiento",
            ]
            if columna in cumplidos_periodo.columns
        ]

        st.dataframe(
            cumplidos_periodo[columnas],
            width="stretch",
            hide_index=True,
            height=min(
                330,
                38 + len(cumplidos_periodo) * 35,
            ),
        )

st.divider()


# ---------------------------------------------------------------------
# DOS ALERTAS CLAVE: PATRONES Y NO CONFORMIDADES
# ---------------------------------------------------------------------

col_pat, col_nc = st.columns(2)

with col_pat:
    st.markdown(
        '<div class="pc-section-title">⚖️ Patrones por atender</div>',
        unsafe_allow_html=True,
    )

    if patrones.empty:
        st.success(
            "No hay patrones vencidos ni próximos a vencer."
        )
    else:
        columnas = [
            columna
            for columna in [
                "codigo_patron",
                "codigo_equipo",
                "nombre_equipo",
                "fecha_vencimiento",
                "dias_restantes",
                "estado_patron",
            ]
            if columna in patrones.columns
        ]

        st.dataframe(
            patrones[columnas],
            width="stretch",
            hide_index=True,
            height=min(
                320,
                38 + len(patrones) * 35,
            ),
        )

with col_nc:
    st.markdown(
        '<div class="pc-section-title">⚠️ Verificaciones por atender</div>',
        unsafe_allow_html=True,
    )

    if no_conformes.empty:
        st.success(
            "No hay verificaciones no conformes o incompletas."
        )
    else:
        columnas = [
            columna
            for columna in [
                "fecha",
                "codigo_equipo",
                "nombre_equipo",
                "estado_sesion",
                "punto",
                "estado_punto",
                "responsable",
            ]
            if columna in no_conformes.columns
        ]

        st.dataframe(
            no_conformes[columnas],
            width="stretch",
            hide_index=True,
            height=min(
                320,
                38 + len(no_conformes) * 35,
            ),
        )

st.divider()


# ---------------------------------------------------------------------
# DETALLE OPERATIVO - OCULTO POR DEFECTO
# ---------------------------------------------------------------------

with st.expander("🔎 Ver detalle operativo", expanded=False):
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("#### Últimas verificaciones")

        if ultimas.empty:
            st.info("Aún no existen sesiones registradas.")
        else:
            columnas = [
                columna
                for columna in [
                    "fecha",
                    "hora",
                    "codigo_equipo",
                    "nombre_equipo",
                    "responsable",
                    "estado",
                ]
                if columna in ultimas.columns
            ]

            st.dataframe(
                ultimas[columnas],
                width="stretch",
                hide_index=True,
            )

    with d2:
        st.markdown("#### Actividad reciente")

        if actividad.empty:
            st.info("La bitácora todavía no tiene eventos.")
        else:
            columnas = [
                columna
                for columna in [
                    "fecha",
                    "hora",
                    "codigo_equipo",
                    "categoria",
                    "evento",
                    "usuario",
                ]
                if columna in actividad.columns
            ]

            st.dataframe(
                actividad[columnas],
                width="stretch",
                hide_index=True,
            )

pie_pagina()