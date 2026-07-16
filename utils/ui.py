import html

import streamlit as st

from config import APP_NAME, APP_SUBTITLE, VERSION

VERDE_PROVIDENCIA = "#1F7A3E"
VERDE_OSCURO = "#155D2E"
AZUL_INCAUCA = "#005AA7"
COLOR_FONDO = "#F4F7F5"
COLOR_TARJETA = "#FFFFFF"
COLOR_TEXTO = "#1F2937"
COLOR_TEXTO_SUAVE = "#64748B"
COLOR_BORDE = "#DDE6E0"


def aplicar_estilo():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(180deg, #FFFFFF 0%, {COLOR_FONDO} 100%);
            color: {COLOR_TEXTO};
        }}

        [data-testid="stSidebar"],
        section[data-testid="stSidebar"] {{
            background: linear-gradient(
                180deg,
                {VERDE_OSCURO} 0%,
                {VERDE_PROVIDENCIA} 65%,
                #25884A 100%
            ) !important;
        }}

        [data-testid="stSidebar"] * {{
            color: #FFFFFF !important;
        }}

        .main-header {{
            padding: 1.45rem 1.7rem;
            border-radius: 20px;
            background: linear-gradient(
                105deg,
                {VERDE_OSCURO} 0%,
                {VERDE_PROVIDENCIA} 75%,
                {AZUL_INCAUCA} 100%
            );
            color: #FFFFFF;
            margin-bottom: 1.25rem;
            box-shadow: 0 8px 24px rgba(15, 76, 42, 0.12);
        }}

        .main-header h1 {{
            color: #FFFFFF !important;
            margin: 0;
            font-size: 2rem;
        }}

        .main-header p {{
            color: rgba(255, 255, 255, 0.95) !important;
            margin: 0.25rem 0 0 0;
        }}

        [data-testid="stMetric"] {{
            background: {COLOR_TARJETA};
            border: 1px solid {COLOR_BORDE};
            border-top: 4px solid {VERDE_PROVIDENCIA};
            border-radius: 16px;
            padding: 1rem;
        }}

        .stButton > button,
        .stFormSubmitButton > button {{
            width: 100%;
            border: none;
            border-radius: 11px;
            background: linear-gradient(100deg, {VERDE_OSCURO}, {VERDE_PROVIDENCIA});
            color: #FFFFFF !important;
            font-weight: 700;
        }}

        .equipment-card {{
            min-height: 310px;
            margin-bottom: 0.9rem;
            padding: 1.15rem;
            border-radius: 16px;
            background: {COLOR_TARJETA};
            border: 1px solid {COLOR_BORDE};
            border-top: 5px solid {VERDE_PROVIDENCIA};
        }}

        .equipment-code {{
            color: {VERDE_OSCURO};
            font-size: 1.35rem;
            font-weight: 800;
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

        .tag-ok,
        .tag-warn,
        .tag-danger,
        .tag-info {{
            display: inline-block;
            padding: 0.28rem 0.70rem;
            border-radius: 999px;
            font-size: 0.80rem;
            font-weight: 750;
        }}

        .tag-ok {{ background: #DCFCE7; color: #166534; }}
        .tag-warn {{ background: #FEF3C7; color: #92400E; }}
        .tag-danger {{ background: #FEE2E2; color: #991B1B; }}
        .tag-info {{ background: #EAF3FB; color: {AZUL_INCAUCA}; }}

        .provicheck-footer {{
            margin-top: 2.4rem;
            padding: 1rem 1.2rem;
            border-top: 1px solid {COLOR_BORDE};
            color: {COLOR_TEXTO_SUAVE};
            text-align: center;
            font-size: 0.84rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def encabezado():
    nombre = html.escape(str(APP_NAME))
    subtitulo = html.escape(str(APP_SUBTITLE))
    version = html.escape(str(VERSION))

    st.markdown(
        f"""
        <div class="main-header">
            <h1>{nombre}</h1>
            <p>{subtitulo} · {version}</p>
            <p><strong>Confiabilidad metrológica para decisiones seguras.</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login_limpio():
    with st.container(border=True):
        st.markdown("### 🔐 Ingreso al sistema")
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        entrar = st.button("Ingresar a PROVICHECK", width="stretch")

        if entrar:
            if usuario.strip() and clave.strip():
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario.strip()
                st.rerun()
            else:
                st.warning("Ingrese usuario y contraseña.")


def estado_class(estado: str):
    texto = str(estado).strip().lower()

    if any(x in texto for x in ["fuera", "inactivo", "baja", "no conforme", "no cumple"]):
        return "tag-danger"

    if any(x in texto for x in ["mant", "calibr", "observ", "incompleta", "pendiente", "no evaluado"]):
        return "tag-warn"

    if any(x in texto for x in ["activo", "operativo", "disponible", "conforme", "cumple"]):
        return "tag-ok"

    return "tag-info"


def tarjeta_equipo(equipo: dict):
    st.markdown(tarjeta_equipo_html(equipo), unsafe_allow_html=True)


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

    return f"""
    <div class="equipment-card">
        <div style="font-size: 2.1rem;">⚖️</div>
        <div class="equipment-code">{codigo}</div>
        <div class="equipment-name">{nombre}</div>
        <div class="equipment-line">🏭 <strong>Laboratorio:</strong> {laboratorio}</div>
        <div class="equipment-line">📍 <strong>Ubicación:</strong> {ubicacion}</div>
        <div class="equipment-line">🏷️ <strong>Tipo:</strong> {tipo}</div>
        <div class="equipment-line">🔧 <strong>Marca / Modelo:</strong> {marca} · {modelo}</div>
        <div class="equipment-line">👤 <strong>Responsable:</strong> {responsable}</div>
        <div class="equipment-line">⚠️ <strong>Criticidad:</strong> {criticidad}</div>
        <p><span class="{estado_class(estado)}">{estado}</span></p>
    </div>
    """


def pie_pagina():
    version = html.escape(str(VERSION))

    st.markdown(
        f"""
        <div class="provicheck-footer">
            <strong>PROVICHECK Enterprise</strong>
            · Gestión inteligente de equipos de laboratorio
            · {version}
        </div>
        """,
        unsafe_allow_html=True,
    )