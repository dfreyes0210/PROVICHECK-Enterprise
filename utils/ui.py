import html

import streamlit as st

from config import APP_NAME, APP_SUBTITLE, VERSION


# ==========================================================
# IDENTIDAD VISUAL PROVICHECK
# ==========================================================

VERDE_PROVIDENCIA = "#1F7A3E"
VERDE_OSCURO = "#155D2E"
VERDE_CLARO = "#EAF6EE"

AZUL_INCAUCA = "#005AA7"
AZUL_CLARO = "#EAF3FB"

COLOR_FONDO = "#F4F7F5"
COLOR_TARJETA = "#FFFFFF"
COLOR_TEXTO = "#1F2937"
COLOR_TEXTO_SUAVE = "#64748B"
COLOR_BORDE = "#DDE6E0"

COLOR_EXITO = "#15803D"
COLOR_ADVERTENCIA = "#D97706"
COLOR_ERROR = "#C62828"

SOMBRA_SUAVE = "0 4px 16px rgba(15, 76, 42, 0.08)"
SOMBRA_MEDIA = "0 8px 24px rgba(15, 76, 42, 0.12)"
RADIO = "16px"


# ==========================================================
# ESTILO GLOBAL
# ==========================================================

def aplicar_estilo():
    st.markdown(
        f"""
        <style>

        /* ==============================================
           BASE GENERAL
        ============================================== */

        :root {{
            --verde-principal: {VERDE_PROVIDENCIA};
            --verde-oscuro: {VERDE_OSCURO};
            --verde-claro: {VERDE_CLARO};
            --azul-secundario: {AZUL_INCAUCA};
            --azul-claro: {AZUL_CLARO};
            --fondo: {COLOR_FONDO};
            --tarjeta: {COLOR_TARJETA};
            --texto: {COLOR_TEXTO};
            --texto-suave: {COLOR_TEXTO_SUAVE};
            --borde: {COLOR_BORDE};
            --exito: {COLOR_EXITO};
            --advertencia: {COLOR_ADVERTENCIA};
            --error: {COLOR_ERROR};
        }}

        html, body, [class*="css"] {{
            font-family:
                Inter,
                "Segoe UI",
                Arial,
                sans-serif;
        }}

        .stApp {{
            background:
                linear-gradient(
                    180deg,
                    #FFFFFF 0%,
                    {COLOR_FONDO} 100%
                );
            color: {COLOR_TEXTO};
        }}

        .block-container {{
            max-width: 1500px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }}

        h1, h2, h3, h4 {{
            color: {COLOR_TEXTO};
            letter-spacing: -0.02em;
        }}

        p, label {{
            color: {COLOR_TEXTO};
        }}

        /* ==============================================
           BARRA LATERAL PROVIDENCIA
        ============================================== */

        [data-testid="stSidebar"] {{
            background:
                linear-gradient(
                    180deg,
                    {VERDE_OSCURO} 0%,
                    {VERDE_PROVIDENCIA} 58%,
                    #25884A 100%
                );
            border-right: none;
            box-shadow: 5px 0 24px rgba(15, 76, 42, 0.18);
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 1.25rem;
        }}

        [data-testid="stSidebar"] * {{
            color: #FFFFFF;
        }}

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{
            color: #FFFFFF !important;
        }}

        [data-testid="stSidebar"] hr {{
            border-color: rgba(255, 255, 255, 0.22);
        }}

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: rgba(255, 255, 255, 0.90);
        }}

        [data-testid="stSidebar"] a {{
            text-decoration: none;
        }}

        [data-testid="stSidebar"] [data-testid="stPageLink"] {{
            border-radius: 10px;
            padding: 0.22rem 0.35rem;
            margin-bottom: 0.20rem;
            transition:
                background 0.2s ease,
                transform 0.2s ease;
        }}

        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover {{
            background: rgba(255, 255, 255, 0.14);
            transform: translateX(3px);
        }}

        /* ==============================================
           ENCABEZADO CORPORATIVO
        ============================================== */

        .main-header {{
            position: relative;
            overflow: hidden;
            padding: 1.45rem 1.7rem;
            border-radius: 20px;
            background:
                linear-gradient(
                    105deg,
                    {VERDE_OSCURO} 0%,
                    {VERDE_PROVIDENCIA} 66%,
                    {AZUL_INCAUCA} 100%
                );
            color: #FFFFFF;
            margin-bottom: 1.25rem;
            box-shadow: {SOMBRA_MEDIA};
        }}

        .main-header::after {{
            content: "";
            position: absolute;
            width: 240px;
            height: 240px;
            right: -95px;
            top: -115px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.10);
        }}

        .main-header::before {{
            content: "";
            position: absolute;
            width: 160px;
            height: 160px;
            right: 65px;
            bottom: -115px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.07);
        }}

        .main-header-content {{
            position: relative;
            z-index: 2;
        }}

        .main-header-brand {{
            display: flex;
            align-items: center;
            gap: 0.80rem;
            margin-bottom: 0.20rem;
        }}

        .main-header-icon {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 50px;
            height: 50px;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.24);
            font-size: 1.65rem;
        }}

        .main-header h1 {{
            color: #FFFFFF !important;
            margin: 0;
            font-size: 2rem;
            font-weight: 750;
            letter-spacing: 0.01em;
        }}

        .main-header .enterprise {{
            color: #FFFFFF;
            font-weight: 400;
        }}

        .main-header p {{
            color: rgba(255, 255, 255, 0.94);
            margin: 0.22rem 0 0 0;
            font-size: 0.98rem;
        }}

        .main-header-slogan {{
            margin-top: 0.55rem !important;
            font-weight: 600;
        }}

        /* ==============================================
           MÉTRICAS Y TARJETAS
        ============================================== */

        [data-testid="stMetric"] {{
            background: {COLOR_TARJETA};
            border: 1px solid {COLOR_BORDE};
            border-top: 4px solid {VERDE_PROVIDENCIA};
            border-radius: {RADIO};
            padding: 1rem 1.05rem;
            box-shadow: {SOMBRA_SUAVE};
            min-height: 118px;
            transition:
                transform 0.20s ease,
                box-shadow 0.20s ease;
        }}

        [data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: {SOMBRA_MEDIA};
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLOR_TEXTO_SUAVE};
            font-weight: 650;
        }}

        [data-testid="stMetricValue"] {{
            color: {VERDE_OSCURO};
            font-weight: 760;
        }}

        [data-testid="stMetricDelta"] {{
            font-weight: 650;
        }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {COLOR_BORDE} !important;
            border-radius: {RADIO} !important;
            background: rgba(255, 255, 255, 0.96);
            box-shadow: {SOMBRA_SUAVE};
        }}

        .equipment-card {{
            min-height: 310px;
            margin-bottom: 0.9rem;
            padding: 1.15rem;
            border-radius: {RADIO};
            background: {COLOR_TARJETA};
            border: 1px solid {COLOR_BORDE};
            border-top: 5px solid {VERDE_PROVIDENCIA};
            box-shadow: {SOMBRA_SUAVE};
            transition:
                transform 0.20s ease,
                box-shadow 0.20s ease,
                border-color 0.20s ease;
        }}

        .equipment-card:hover {{
            transform: translateY(-3px);
            box-shadow: {SOMBRA_MEDIA};
            border-color: {VERDE_PROVIDENCIA};
        }}

        .equipment-code {{
            color: {VERDE_OSCURO};
            font-size: 1.35rem;
            font-weight: 800;
            margin-top: 0.35rem;
        }}

        .equipment-name {{
            color: {COLOR_TEXTO};
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 0.85rem;
        }}

        .equipment-line {{
            color: {COLOR_TEXTO_SUAVE};
            font-size: 0.90rem;
            line-height: 1.55;
            margin-bottom: 0.25rem;
        }}

        /* ==============================================
           ETIQUETAS DE ESTADO
        ============================================== */

        .tag-ok,
        .tag-warn,
        .tag-danger,
        .tag-info {{
            display: inline-block;
            padding: 0.28rem 0.70rem;
            border-radius: 999px;
            font-size: 0.80rem;
            font-weight: 750;
            line-height: 1.2;
        }}

        .tag-ok {{
            background: #DCFCE7;
            color: #166534;
            border: 1px solid #BBF7D0;
        }}

        .tag-warn {{
            background: #FEF3C7;
            color: #92400E;
            border: 1px solid #FDE68A;
        }}

        .tag-danger {{
            background: #FEE2E2;
            color: #991B1B;
            border: 1px solid #FECACA;
        }}

        .tag-info {{
            background: {AZUL_CLARO};
            color: {AZUL_INCAUCA};
            border: 1px solid #BFDBFE;
        }}

        /* ==============================================
           BOTONES
        ============================================== */

        .stButton > button,
        .stFormSubmitButton > button {{
            width: 100%;
            min-height: 42px;
            border: none;
            border-radius: 11px;
            background:
                linear-gradient(
                    100deg,
                    {VERDE_OSCURO},
                    {VERDE_PROVIDENCIA}
                );
            color: #FFFFFF !important;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(31, 122, 62, 0.20);
            transition:
                transform 0.18s ease,
                box-shadow 0.18s ease,
                filter 0.18s ease;
        }}

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{
            transform: translateY(-1px);
            filter: brightness(1.04);
            box-shadow: 0 7px 18px rgba(31, 122, 62, 0.28);
        }}

        .stButton > button:active,
        .stFormSubmitButton > button:active {{
            transform: translateY(0);
        }}

        [data-testid="stSidebar"] .stButton > button {{
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.28);
            box-shadow: none;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255, 255, 255, 0.20);
        }}

        /* ==============================================
           CAMPOS DE FORMULARIO
        ============================================== */

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] {{
            border-radius: 10px !important;
            border-color: {COLOR_BORDE} !important;
            background: #FFFFFF !important;
        }}

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"]:focus-within {{
            border-color: {VERDE_PROVIDENCIA} !important;
            box-shadow: 0 0 0 2px rgba(31, 122, 62, 0.12) !important;
        }}

        /* ==============================================
           PESTAÑAS
        ============================================== */

        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.35rem;
            padding: 0.30rem;
            border-radius: 12px;
            background: #EDF3EF;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 44px;
            padding: 0 0.95rem;
            border-radius: 9px;
            color: {COLOR_TEXTO_SUAVE};
            font-weight: 650;
        }}

        .stTabs [aria-selected="true"] {{
            color: #FFFFFF !important;
            background:
                linear-gradient(
                    100deg,
                    {VERDE_OSCURO},
                    {VERDE_PROVIDENCIA}
                ) !important;
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            display: none;
        }}

        /* ==============================================
           MENSAJES
        ============================================== */

        [data-testid="stAlert"] {{
            border-radius: 12px;
            border-width: 1px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        }}

        /* ==============================================
           TABLAS Y DATAFRAMES
        ============================================== */

        [data-testid="stDataFrame"] {{
            overflow: hidden;
            border: 1px solid {COLOR_BORDE};
            border-radius: 13px;
            box-shadow: {SOMBRA_SUAVE};
        }}

        [data-testid="stTable"] {{
            border-radius: 13px;
            overflow: hidden;
        }}

        /* ==============================================
           DIVISORES Y ENLACES
        ============================================== */

        hr {{
            border: none;
            height: 1px;
            background:
                linear-gradient(
                    90deg,
                    transparent,
                    {COLOR_BORDE},
                    transparent
                );
            margin: 1.2rem 0;
        }}

        a {{
            color: {AZUL_INCAUCA};
        }}

        /* ==============================================
           PIE DE PÁGINA
        ============================================== */

        .provicheck-footer {{
            margin-top: 2.4rem;
            padding: 1rem 1.2rem;
            border-top: 1px solid {COLOR_BORDE};
            color: {COLOR_TEXTO_SUAVE};
            text-align: center;
            font-size: 0.84rem;
        }}

        .provicheck-footer strong {{
            color: {VERDE_OSCURO};
        }}

        /* ==============================================
           RESPONSIVE
        ============================================== */

        @media (max-width: 900px) {{
            .main-header {{
                padding: 1.15rem;
            }}

            .main-header h1 {{
                font-size: 1.55rem;
            }}

            .main-header-icon {{
                width: 43px;
                height: 43px;
                font-size: 1.35rem;
            }}

            [data-testid="stMetric"] {{
                min-height: 105px;
            }}
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# ENCABEZADO
# ==========================================================

def encabezado():
    nombre_seguro = html.escape(str(APP_NAME))
    subtitulo_seguro = html.escape(str(APP_SUBTITLE))
    version_segura = html.escape(str(VERSION))

    st.markdown(
        f"""
        <div class="main-header">
            <div class="main-header-content">
                <div class="main-header-brand">
                    <div class="main-header-icon">🧪</div>
                    <div>
                        <h1>{nombre_seguro} <span class="enterprise">Enterprise</span></h1>
                        <p>{subtitulo_seguro} · {version_segura}</p>
                    </div>
                </div>

                <p class="main-header-slogan">
                    Confiabilidad metrológica para decisiones seguras.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# LOGIN
# ==========================================================

def login_limpio():
    with st.container(border=True):
        st.markdown("### 🔐 Ingreso al sistema")
        st.caption("Acceso exclusivo para usuarios autorizados.")

        usuario = st.text_input(
            "Usuario",
            placeholder="Ingrese su usuario",
        )

        clave = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Ingrese su contraseña",
        )

        entrar = st.button(
            "Ingresar a PROVICHECK",
            width="stretch",
        )

        if entrar:
            usuario_limpio = usuario.strip()
            clave_limpia = clave.strip()

            if usuario_limpio and clave_limpia:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario_limpio
                st.rerun()
            else:
                st.warning("Ingrese usuario y contraseña.")


# ==========================================================
# ESTADOS
# ==========================================================

def estado_class(estado: str):
    texto = str(estado).strip().lower()

    if (
        "fuera" in texto
        or "inactivo" in texto
        or "baja" in texto
        or "no conforme" in texto
        or "no cumple" in texto
    ):
        return "tag-danger"

    if (
        "mant" in texto
        or "calibr" in texto
        or "observ" in texto
        or "incompleta" in texto
        or "pendiente" in texto
        or "no evaluado" in texto
    ):
        return "tag-warn"

    if (
        "activo" in texto
        or "operativo" in texto
        or "disponible" in texto
        or "conforme" in texto
        or "cumple" in texto
    ):
        return "tag-ok"

    return "tag-info"


# ==========================================================
# TARJETAS DE EQUIPO
# ==========================================================

def tarjeta_equipo(equipo: dict):
    st.markdown(
        tarjeta_equipo_html(equipo),
        unsafe_allow_html=True,
    )


def tarjeta_equipo_html(equipo: dict):
    codigo = html.escape(str(equipo.get("codigo_equipo", "Sin código")))
    nombre = html.escape(str(equipo.get("nombre_equipo", "Equipo sin nombre")))
    laboratorio = html.escape(str(equipo.get("laboratorio", "Sin laboratorio")))
    ubicacion = html.escape(str(equipo.get("ubicacion", "Sin ubicación")))
    estado = html.escape(str(equipo.get("estado", "Sin estado")))
    responsable = html.escape(str(equipo.get("responsable", "Sin responsable")))
    criticidad = html.escape(str(equipo.get("criticidad", "Sin criticidad")))
    marca = html.escape(str(equipo.get("marca", "Sin marca")))
    modelo = html.escape(str(equipo.get("modelo", "Sin modelo")))
    tipo = html.escape(str(equipo.get("tipo_equipo", "Sin tipo")))

    clase_estado = estado_class(estado)

    return f"""
    <div class="equipment-card">
        <div style="font-size: 2.1rem;">⚖️</div>

        <div class="equipment-code">{codigo}</div>
        <div class="equipment-name">{nombre}</div>

        <div class="equipment-line">
            🏭 <strong>Laboratorio:</strong> {laboratorio}
        </div>

        <div class="equipment-line">
            📍 <strong>Ubicación:</strong> {ubicacion}
        </div>

        <div class="equipment-line">
            🏷️ <strong>Tipo:</strong> {tipo}
        </div>

        <div class="equipment-line">
            🔧 <strong>Marca / Modelo:</strong> {marca} · {modelo}
        </div>

        <div class="equipment-line">
            👤 <strong>Responsable:</strong> {responsable}
        </div>

        <div class="equipment-line">
            ⚠️ <strong>Criticidad:</strong> {criticidad}
        </div>

        <p style="margin-top: 0.85rem;">
            <span class="{clase_estado}">{estado}</span>
        </p>
    </div>
    """


# ==========================================================
# PIE DE PÁGINA
# ==========================================================

def pie_pagina():
    version_segura = html.escape(str(VERSION))

    st.markdown(
        f"""
        <div class="provicheck-footer">
            <strong>PROVICHECK Enterprise</strong>
            · Gestión inteligente de equipos de laboratorio
            · {version_segura}
        </div>
        """,
        unsafe_allow_html=True,
    )