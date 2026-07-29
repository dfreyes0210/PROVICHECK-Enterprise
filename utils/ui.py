import html
import hmac

import streamlit as st
from config import APP_NAME, APP_SUBTITLE, VERSION

VERDE_PROVIDENCIA = '#147A3B'
VERDE_OSCURO = '#075E32'
AZUL_INCAUCA = '#0759C7'
AZUL_OSCURO = '#073B8C'
COLOR_FONDO = '#F5F8FC'
COLOR_TARJETA = '#FFFFFF'
COLOR_TEXTO = '#0F2747'
COLOR_TEXTO_SUAVE = '#5F718A'
COLOR_BORDE = '#D5E1F0'


def aplicar_estilo():
    st.markdown('''

    <style>
    :root {
        --pc-green:#147A3B;
        --pc-green-dark:#075E32;
        --pc-blue:#0759C7;
        --pc-blue-dark:#073B8C;
        --pc-bg:#F5F8FC;
        --pc-text:#0F2747;
        --pc-muted:#5F718A;
        --pc-border:#D5E1F0;
    }

    html, body, [class*="css"] {
        font-family:"Segoe UI",Arial,sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top right,rgba(7,89,199,.06),transparent 28%),
            linear-gradient(180deg,#FFFFFF 0%,var(--pc-bg) 100%);
        color:var(--pc-text);
    }

    .block-container {
        max-width:1500px;
        padding-top:1rem;
        padding-bottom:2rem;
    }

    h1,h2,h3,h4,h5,h6,p,label,span {
        color:var(--pc-text);
    }

    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color:var(--pc-muted)!important;
    }

    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background:linear-gradient(
            180deg,
            var(--pc-green-dark) 0%,
            #08633E 42%,
            #064C58 72%,
            var(--pc-blue-dark) 100%
        )!important;
        border-right:1px solid rgba(255,255,255,.08);
    }

    [data-testid="stSidebar"] * {
        color:#FFFFFF!important;
    }

    [data-testid="stSidebarNav"] {
        display:none!important;
    }

    [data-testid="stSidebar"] hr {
        border-color:rgba(255,255,255,.18)!important;
    }

    [data-testid="stSidebar"] a {
        border-radius:10px;
        padding:.28rem .42rem;
        transition:.2s ease;
    }

    [data-testid="stSidebar"] a:hover {
        background:linear-gradient(
            90deg,
            rgba(29,184,93,.85),
            rgba(7,89,199,.82)
        );
    }

    .sidebar-brand {
        padding:.35rem .2rem .65rem;
    }

    .sidebar-brand-title {
        color:#FFF!important;
        font-size:1.28rem;
        font-weight:850;
    }

    .sidebar-brand-subtitle {
        color:rgba(255,255,255,.74)!important;
        font-size:.78rem;
    }

    .sidebar-user {
        margin-top:.45rem;
        padding:.8rem;
        border:1px solid rgba(255,255,255,.18);
        background:rgba(255,255,255,.08);
        border-radius:13px;
    }

    .sidebar-user strong,
    .sidebar-user span {
        color:#FFF!important;
    }

    .main-header {
        padding:1.05rem 1.35rem;
        border-radius:15px;
        background:linear-gradient(
            100deg,
            var(--pc-green-dark) 0%,
            var(--pc-green) 30%,
            #087E79 58%,
            var(--pc-blue) 100%
        );
        color:#FFF;
        margin-bottom:1.1rem;
        box-shadow:0 10px 28px rgba(7,59,140,.16);
    }

    .main-header h1 {
        color:#FFF!important;
        margin:0;
        font-size:1.2rem;
        font-weight:800;
    }

    .main-header p {
        color:rgba(255,255,255,.96)!important;
        margin:.18rem 0 0;
        font-size:.86rem;
    }

    [data-testid="stMetric"] {
        background:linear-gradient(145deg,#FFF 0%,#FBFDFF 100%);
        border:1px solid var(--pc-border);
        border-top:3px solid var(--pc-green);
        border-radius:14px;
        padding:.9rem 1rem;
        box-shadow:0 5px 16px rgba(15,39,71,.05);
    }

    [data-testid="stMetricLabel"] p {
        color:var(--pc-muted)!important;
        font-weight:700!important;
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {
        color:var(--pc-text)!important;
        font-weight:850!important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border:1px solid var(--pc-border)!important;
        border-radius:15px!important;
        background:linear-gradient(145deg,#FFF,#FBFDFF)!important;
        box-shadow:0 5px 16px rgba(15,39,71,.055);
    }

    div[data-testid="stForm"] {
        background:#FFF!important;
        border:1px solid var(--pc-border)!important;
        border-radius:14px!important;
        padding:1rem!important;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stTimeInput"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stFileUploader"] label,
    div[data-testid="stCheckbox"] label {
        color:var(--pc-text)!important;
        font-weight:700!important;
        opacity:1!important;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    div[data-testid="stDateInput"] input,
    div[data-testid="stTimeInput"] input {
        background:#FFF!important;
        color:var(--pc-text)!important;
        -webkit-text-fill-color:var(--pc-text)!important;
        border:1px solid #BFD0E5!important;
        border-radius:9px!important;
        opacity:1!important;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    div[data-testid="stDateInput"] input:focus,
    div[data-testid="stTimeInput"] input:focus {
        border-color:var(--pc-blue)!important;
        box-shadow:0 0 0 2px rgba(7,89,199,.13)!important;
    }

    input::placeholder,
    textarea::placeholder {
        color:#8291A6!important;
        -webkit-text-fill-color:#8291A6!important;
        opacity:1!important;
    }

    input:disabled,
    textarea:disabled,
    [data-disabled="true"] {
        background:#EEF2F7!important;
        color:#6C7B90!important;
        -webkit-text-fill-color:#6C7B90!important;
        opacity:1!important;
    }

    [data-baseweb="select"]>div {
        background:#FFF!important;
        color:var(--pc-text)!important;
        border:1px solid #BFD0E5!important;
        border-radius:9px!important;
    }

    [data-baseweb="select"] *,
    [data-testid="stSelectbox"] * {
        color:var(--pc-text)!important;
        -webkit-text-fill-color:var(--pc-text)!important;
    }

    [data-baseweb="select"]>div:focus-within {
        border-color:var(--pc-blue)!important;
        box-shadow:0 0 0 2px rgba(7,89,199,.13)!important;
    }

    [data-baseweb="popover"] ul {
        background:#FFF!important;
        border:1px solid var(--pc-border)!important;
    }

    [role="option"] {
        background:#FFF!important;
        color:var(--pc-text)!important;
    }

    [role="option"]:hover {
        background:#EAF7EF!important;
    }

    [aria-selected="true"][role="option"] {
        background:#EAF3FF!important;
        color:var(--pc-blue-dark)!important;
        font-weight:700!important;
    }

    div[data-testid="stNumberInput"] button {
        background:linear-gradient(
            135deg,
            var(--pc-green),
            var(--pc-blue)
        )!important;
        color:#FFF!important;
        border:0!important;
    }

    div[data-testid="stNumberInput"] button * {
        color:#FFF!important;
        fill:#FFF!important;
    }

    div[data-testid="stCheckbox"] span[aria-checked="true"] {
        background:var(--pc-green)!important;
        border-color:var(--pc-green)!important;
    }

    div[data-testid="stCheckbox"] span[aria-checked="false"] {
        background:#FFF!important;
        border-color:#9EB0C7!important;
    }

    .stButton>button,
    .stFormSubmitButton>button,
    .stDownloadButton>button {
        width:100%;
        border:0;
        border-radius:10px;
        background:linear-gradient(
            100deg,
            var(--pc-green-dark),
            var(--pc-green),
            var(--pc-blue)
        );
        color:#FFF!important;
        font-weight:800;
        min-height:2.55rem;
        box-shadow:0 6px 16px rgba(7,89,199,.15);
        transition:.18s ease;
    }

    .stButton>button *,
    .stFormSubmitButton>button *,
    .stDownloadButton>button * {
        color:#FFF!important;
    }

    .stButton>button:hover,
    .stFormSubmitButton>button:hover,
    .stDownloadButton>button:hover {
        filter:brightness(1.06);
        transform:translateY(-1px);
    }

    .stButton>button:disabled,
    .stFormSubmitButton>button:disabled {
        background:#C7D1DF!important;
        color:#66758A!important;
        box-shadow:none!important;
        transform:none!important;
    }

    div[data-testid="stExpander"] details {
        border:1px solid var(--pc-border)!important;
        border-radius:12px!important;
        overflow:hidden;
        background:#FFF!important;
    }

    div[data-testid="stExpander"] summary {
        background:linear-gradient(
            100deg,
            var(--pc-green-dark),
            var(--pc-green),
            var(--pc-blue)
        )!important;
        min-height:2.9rem;
    }

    div[data-testid="stExpander"] summary *,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {
        color:#FFF!important;
        fill:#FFF!important;
        opacity:1!important;
        font-weight:750!important;
    }

    div[data-baseweb="tab-list"] {
        gap:.28rem;
        border-bottom:1px solid var(--pc-border);
    }

    button[data-baseweb="tab"] {
        background:#FFF!important;
        border:1px solid var(--pc-border)!important;
        border-bottom:0!important;
        border-radius:9px 9px 0 0!important;
        padding:.5rem .75rem!important;
    }

    button[data-baseweb="tab"] * {
        color:var(--pc-muted)!important;
        font-weight:700!important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background:linear-gradient(
            100deg,
            var(--pc-green-dark),
            var(--pc-green),
            var(--pc-blue)
        )!important;
        border-color:transparent!important;
    }

    button[data-baseweb="tab"][aria-selected="true"] * {
        color:#FFF!important;
    }

    div[data-testid="stFileUploader"] section {
        background:#F8FBFF!important;
        border:1px dashed #9FB5CF!important;
        border-radius:12px!important;
    }

    div[data-testid="stFileUploader"] section *,
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] p,
    div[data-testid="stFileUploader"] span {
        color:var(--pc-text)!important;
        opacity:1!important;
    }

    div[data-testid="stFileUploader"] button {
        background:linear-gradient(
            100deg,
            var(--pc-green),
            var(--pc-blue)
        )!important;
        color:#FFF!important;
        border:0!important;
    }

    [data-baseweb="calendar"],
    [data-baseweb="calendar"] * {
        color:var(--pc-text)!important;
    }

    [data-baseweb="calendar"] {
        background:#FFF!important;
        border:1px solid var(--pc-border)!important;
    }

    [data-baseweb="calendar"] button[aria-selected="true"] {
        background:var(--pc-green)!important;
        color:#FFF!important;
    }

    [data-testid="stDataFrame"] {
        border:1px solid var(--pc-border);
        border-radius:12px;
        overflow:hidden;
    }

    .stAlert {
        border-radius:12px!important;
    }

    .equipment-card {
        min-height:315px;
        margin-bottom:.8rem;
        padding:1.05rem;
        border-radius:15px;
        background:linear-gradient(145deg,#FFF,#FBFDFF);
        border:1px solid var(--pc-border);
        border-top:4px solid var(--pc-green);
        box-shadow:0 7px 20px rgba(15,39,71,.055);
    }

    .equipment-code {
        color:var(--pc-blue);
        font-size:1.25rem;
        font-weight:850;
    }

    .equipment-name {
        color:var(--pc-text);
        font-size:1rem;
        font-weight:750;
        margin-bottom:.75rem;
    }

    .equipment-line {
        color:var(--pc-muted);
        font-size:.88rem;
        line-height:1.48;
        margin-bottom:.24rem;
    }

    .equipment-line strong {
        color:var(--pc-text);
    }

    .verification-card-title {
        display:flex;
        align-items:center;
        gap:.55rem;
        margin-bottom:.15rem;
        font-size:1.08rem;
        font-weight:850;
        color:var(--pc-text);
    }

    .verification-card-badge {
        width:2.1rem;
        height:2.1rem;
        display:inline-flex;
        align-items:center;
        justify-content:center;
        border-radius:50%;
        background:linear-gradient(135deg,#EAF8EF,#EAF3FF);
        border:1px solid #C7DDF4;
    }

    .tag-ok,.tag-warn,.tag-danger,.tag-info {
        display:inline-block;
        padding:.25rem .64rem;
        border-radius:999px;
        font-size:.78rem;
        font-weight:800;
    }

    .tag-ok {background:#DCFCE7;color:#166534;}
    .tag-warn {background:#FEF3C7;color:#92400E;}
    .tag-danger {background:#FEE2E2;color:#991B1B;}
    .tag-info {background:#EAF3FF;color:var(--pc-blue);}

    .provicheck-footer {
        margin-top:2rem;
        padding:.9rem 1rem;
        border-top:1px solid var(--pc-border);
        color:var(--pc-muted);
        text-align:center;
        font-size:.82rem;
    }
    </style>

    ''', unsafe_allow_html=True)


def encabezado():
    st.markdown(f'''
    <div class="main-header">
        <h1>🛡️ {html.escape(str(APP_NAME))} · {html.escape(str(VERSION))}</h1>
        <p>{html.escape(str(APP_SUBTITLE))}</p>
        <p><strong>Confiabilidad metrológica para decisiones seguras.</strong></p>
    </div>
    ''', unsafe_allow_html=True)



def _normalizar_texto(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.lower() in {"nan", "nat", "none"}:
        return ""
    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base
    return texto


def _normalizar_rol(valor):
    rol = _normalizar_texto(valor).lower()
    equivalencias = {
        "administrador": "Administrador",
        "admin": "Administrador",
        "líder": "Líder",
        "lider": "Líder",
        "supervisor": "Líder",
        "analista": "Analista",
    }
    return equivalencias.get(rol, _normalizar_texto(valor) or "Analista")


def _usuario_autorizado(usuario_ingresado, clave_ingresada):
    from utils.data import cargar_usuarios

    usuarios = cargar_usuarios()
    if usuarios.empty:
        return None, (
            "No fue posible consultar la hoja Usuarios de la base maestra."
        )

    usuarios = usuarios.copy()
    usuarios.columns = [
        str(columna).strip().lower()
        for columna in usuarios.columns
    ]

    columnas_requeridas = {
        "nombre_usuario",
        "usuario_login",
        "clave",
        "rol",
        "laboratorio_asignado",
        "estado_usuario",
    }
    faltantes = columnas_requeridas.difference(usuarios.columns)
    if faltantes:
        return None, (
            "La hoja Usuarios no tiene todas las columnas requeridas: "
            + ", ".join(sorted(faltantes))
        )

    usuario_busqueda = _normalizar_texto(usuario_ingresado).lower()
    clave_busqueda = _normalizar_texto(clave_ingresada)

    coincidencias = usuarios[
        usuarios["usuario_login"]
        .apply(_normalizar_texto)
        .str.lower()
        .eq(usuario_busqueda)
    ].copy()

    if coincidencias.empty:
        return None, "Usuario o contraseña incorrectos."

    coincidencias["clave_normalizada"] = (
        coincidencias["clave"].apply(_normalizar_texto)
    )
    coincidencias = coincidencias[
        coincidencias["clave_normalizada"].apply(
            lambda valor: hmac.compare_digest(valor, clave_busqueda)
        )
    ]

    if coincidencias.empty:
        return None, "Usuario o contraseña incorrectos."

    if len(coincidencias) > 1:
        return None, (
            "Existe más de un registro con las mismas credenciales. "
            "Solicite al administrador corregir la hoja Usuarios."
        )

    fila = coincidencias.iloc[0]
    estado = _normalizar_texto(fila.get("estado_usuario")).lower()
    if estado not in {"activo", "activa", "sí", "si", "1", "true"}:
        return None, "El usuario se encuentra inactivo."

    datos = {
        "id_usuario": _normalizar_texto(fila.get("id_usuario")),
        "nombre_usuario": _normalizar_texto(
            fila.get("nombre_usuario")
        ),
        "usuario": _normalizar_texto(fila.get("usuario_login")),
        "rol": _normalizar_rol(fila.get("rol")),
        "laboratorio_asignado": _normalizar_texto(
            fila.get("laboratorio_asignado")
        ) or "Todos",
        "correo": _normalizar_texto(fila.get("correo")),
    }
    return datos, None


def cerrar_sesion():
    claves_usuario = [
        "autenticado",
        "id_usuario",
        "nombre_usuario",
        "usuario",
        "rol",
        "laboratorio_asignado",
        "correo",
        "equipo_seleccionado",
    ]
    for clave in claves_usuario:
        st.session_state.pop(clave, None)
    st.session_state["autenticado"] = False


def requerir_autenticacion(roles_permitidos=None):
    if not st.session_state.get("autenticado", False):
        st.warning(
            "La sesión no está activa. Ingrese nuevamente desde el Dashboard."
        )
        st.page_link("app.py", label="🔐 Ir al inicio de sesión")
        st.stop()

    if roles_permitidos:
        rol_actual = _normalizar_rol(st.session_state.get("rol"))
        permitidos = {
            _normalizar_rol(rol)
            for rol in roles_permitidos
        }
        if rol_actual not in permitidos:
            st.error(
                "Su perfil no tiene autorización para ingresar a este módulo."
            )
            st.page_link("app.py", label="🏠 Volver al Dashboard")
            st.stop()


def sidebar_pro():
    requerir_autenticacion()

    usuario = html.escape(
        str(
            st.session_state.get(
                "nombre_usuario",
                st.session_state.get("usuario", ""),
            )
        )
    )
    rol_original = _normalizar_rol(st.session_state.get("rol"))
    rol = html.escape(rol_original)
    laboratorio = html.escape(
        str(st.session_state.get("laboratorio_asignado", "Todos"))
    )

    with st.sidebar:
        st.markdown(f'''
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">🛡️ PROVICHECK</div>
            <div class="sidebar-brand-subtitle">Enterprise · {html.escape(str(VERSION))}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.page_link("app.py", label="🏠 Dashboard")
        st.page_link("pages/01_Equipos.py", label="🧪 Equipos")
        st.page_link("pages/02_Hoja_de_Vida.py", label="📘 Hoja de Vida")
        st.page_link("pages/04_Verificaciones.py", label="✅ Verificaciones")

        if rol_original == "Administrador":
            st.page_link(
                "pages/03_Administracion.py",
                label="⚙️ Administración",
            )

        st.divider()
        st.markdown(f'''
        <div class="sidebar-user">
            <strong>👤 {usuario or 'Usuario'}</strong><br>
            <span>Rol: {rol}</span><br>
            <span>Laboratorio: {laboratorio}</span><br>
            <span>🟢 Sesión activa</span>
        </div>
        ''', unsafe_allow_html=True)
        st.divider()

        if st.button("↪ Cerrar sesión", width="stretch"):
            cerrar_sesion()
            st.rerun()


def login_limpio():
    with st.container(border=True):
        st.markdown("### 🔐 Ingreso al sistema")
        usuario = st.text_input(
            "Usuario",
            key="login_usuario",
        )
        clave = st.text_input(
            "Contraseña",
            type="password",
            key="login_clave",
        )
        entrar = st.button(
            "Ingresar a PROVICHECK",
            width="stretch",
            type="primary",
        )

        if entrar:
            if not usuario.strip() or not clave.strip():
                st.warning("Ingrese usuario y contraseña.")
                return

            datos_usuario, error = _usuario_autorizado(
                usuario,
                clave,
            )

            if error:
                st.error(error)
                return

            cerrar_sesion()
            st.session_state["autenticado"] = True
            for clave_estado, valor in datos_usuario.items():
                st.session_state[clave_estado] = valor

            st.success(
                f"Bienvenido(a), {datos_usuario['nombre_usuario']}."
            )
            st.rerun()

def estado_class(estado: str):
    texto = str(estado).strip().lower()
    if any(x in texto for x in ['fuera','inactivo','baja','no conforme','no cumple']): return 'tag-danger'
    if any(x in texto for x in ['mant','calibr','observ','incompleta','pendiente','no evaluado']): return 'tag-warn'
    if any(x in texto for x in ['activo','operativo','disponible','conforme','cumple']): return 'tag-ok'
    return 'tag-info'


def tarjeta_equipo(equipo: dict):
    st.markdown(tarjeta_equipo_html(equipo), unsafe_allow_html=True)


def tarjeta_equipo_html(equipo: dict):
    e = {k: html.escape(str(v)) for k,v in equipo.items()}
    codigo=e.get('codigo_equipo','Sin código'); nombre=e.get('nombre_equipo','Equipo sin nombre')
    laboratorio=e.get('laboratorio','Sin laboratorio'); ubicacion=e.get('ubicacion','Sin ubicación')
    estado=e.get('estado','Sin estado'); responsable=e.get('responsable','Sin responsable')
    criticidad=e.get('criticidad','Sin criticidad'); marca=e.get('marca','Sin marca')
    modelo=e.get('modelo','Sin modelo'); tipo=e.get('tipo_equipo','Sin tipo')
    return f'''
    <div class="equipment-card">
        <div style="font-size:1.9rem;">⚖️</div>
        <div class="equipment-code">{codigo}</div>
        <div class="equipment-name">{nombre}</div>
        <div class="equipment-line">🏭 <strong>Laboratorio:</strong> {laboratorio}</div>
        <div class="equipment-line">📍 <strong>Ubicación:</strong> {ubicacion}</div>
        <div class="equipment-line">🏷️ <strong>Tipo:</strong> {tipo}</div>
        <div class="equipment-line">🔧 <strong>Marca / Modelo:</strong> {marca} · {modelo}</div>
        <div class="equipment-line">👤 <strong>Responsable:</strong> {responsable}</div>
        <div class="equipment-line">⚠️ <strong>Criticidad:</strong> {criticidad}</div>
        <p><span class="{estado_class(estado)}">{estado}</span></p>
    </div>'''


def pie_pagina():
    st.markdown(f'''
    <div class="provicheck-footer"><strong>PROVICHECK Enterprise</strong> · Gestión inteligente de equipos de laboratorio · {html.escape(str(VERSION))}</div>
    ''', unsafe_allow_html=True)