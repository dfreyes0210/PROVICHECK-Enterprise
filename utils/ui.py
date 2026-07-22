import html
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
    st.markdown(f'''
    <style>
    html, body, [class*="css"] {{ font-family: "Segoe UI", Arial, sans-serif; }}
    .stApp {{
        background: radial-gradient(circle at top right, rgba(7,89,199,.06), transparent 28%),
                    linear-gradient(180deg,#FFFFFF 0%,{COLOR_FONDO} 100%);
        color:{COLOR_TEXTO};
    }}
    .block-container {{ max-width:1500px; padding-top:1rem; padding-bottom:2rem; }}
    h1,h2,h3,h4,h5,h6,p,label,span {{ color:{COLOR_TEXTO}; }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:{COLOR_TEXTO_SUAVE}!important; }}

    [data-testid="stSidebar"], section[data-testid="stSidebar"] {{
        background:linear-gradient(180deg,{VERDE_OSCURO} 0%,#08633E 42%,#064C58 72%,{AZUL_OSCURO} 100%)!important;
        border-right:1px solid rgba(255,255,255,.08);
    }}
    [data-testid="stSidebar"] * {{ color:#FFFFFF!important; }}
    [data-testid="stSidebar"] hr {{ border-color:rgba(255,255,255,.18)!important; }}
    [data-testid="stSidebar"] a {{ border-radius:10px; padding:.28rem .42rem; transition:.2s ease; }}
    [data-testid="stSidebar"] a:hover {{ background:linear-gradient(90deg,rgba(29,184,93,.85),rgba(7,89,199,.82)); }}
    .sidebar-brand {{ padding:.35rem .2rem .65rem; }}
    .sidebar-brand-title {{ color:#FFF!important; font-size:1.28rem; font-weight:850; }}
    .sidebar-brand-subtitle {{ color:rgba(255,255,255,.74)!important; font-size:.78rem; }}
    .sidebar-user {{ margin-top:.45rem; padding:.8rem; border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.08); border-radius:13px; }}
    .sidebar-user strong,.sidebar-user span {{ color:#FFF!important; }}

    .main-header {{
        padding:1.05rem 1.35rem; border-radius:15px;
        background:linear-gradient(100deg,{VERDE_OSCURO} 0%,{VERDE_PROVIDENCIA} 30%,#087E79 58%,{AZUL_INCAUCA} 100%);
        color:#FFF; margin-bottom:1.1rem; box-shadow:0 10px 28px rgba(7,59,140,.16);
    }}
    .main-header h1 {{ color:#FFF!important; margin:0; font-size:1.2rem; font-weight:800; }}
    .main-header p {{ color:rgba(255,255,255,.96)!important; margin:.18rem 0 0; font-size:.86rem; }}

    [data-testid="stMetric"] {{
        background:linear-gradient(145deg,#FFF 0%,#FBFDFF 100%); border:1px solid {COLOR_BORDE};
        border-top:3px solid {VERDE_PROVIDENCIA}; border-radius:14px; padding:.9rem 1rem;
        box-shadow:0 5px 16px rgba(15,39,71,.05);
    }}
    [data-testid="stMetricLabel"] p {{ color:{COLOR_TEXTO_SUAVE}!important; font-weight:700!important; }}
    [data-testid="stMetricValue"] {{ color:{COLOR_TEXTO}!important; font-weight:850!important; }}
    [data-testid="stMetricDelta"] div {{ font-weight:700!important; }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border:1px solid {COLOR_BORDE}!important; border-radius:15px!important;
        background:linear-gradient(145deg,#FFF,#FBFDFF)!important;
        box-shadow:0 5px 16px rgba(15,39,71,.055);
    }}
    .stTextInput input,.stNumberInput input,.stTextArea textarea,[data-baseweb="select"]>div {{
        background:#FFF!important; color:{COLOR_TEXTO}!important; border-color:#BFD0E5!important; border-radius:9px!important;
    }}
    .stTextInput label,.stNumberInput label,.stTextArea label,.stSelectbox label,.stFileUploader label {{ color:{COLOR_TEXTO}!important; font-weight:700!important; }}

    .stButton>button,.stFormSubmitButton>button {{
        width:100%; border:0; border-radius:10px;
        background:linear-gradient(100deg,{VERDE_OSCURO},{VERDE_PROVIDENCIA},{AZUL_INCAUCA});
        color:#FFF!important; font-weight:800; min-height:2.55rem; box-shadow:0 6px 16px rgba(7,89,199,.15);
    }}
    .stButton>button:hover,.stFormSubmitButton>button:hover {{ filter:brightness(1.06); transform:translateY(-1px); }}

    .equipment-card {{
        min-height:315px; margin-bottom:.8rem; padding:1.05rem; border-radius:15px;
        background:linear-gradient(145deg,#FFF,#FBFDFF); border:1px solid {COLOR_BORDE};
        border-top:4px solid {VERDE_PROVIDENCIA}; box-shadow:0 7px 20px rgba(15,39,71,.055);
    }}
    .equipment-code {{ color:{AZUL_INCAUCA}; font-size:1.25rem; font-weight:850; }}
    .equipment-name {{ color:{COLOR_TEXTO}; font-size:1rem; font-weight:750; margin-bottom:.75rem; }}
    .equipment-line {{ color:{COLOR_TEXTO_SUAVE}; font-size:.88rem; line-height:1.48; margin-bottom:.24rem; }}
    .equipment-line strong {{ color:{COLOR_TEXTO}; }}

    .verification-card-title {{ display:flex; align-items:center; gap:.55rem; margin-bottom:.15rem; font-size:1.08rem; font-weight:850; color:{COLOR_TEXTO}; }}
    .verification-card-badge {{ width:2.1rem; height:2.1rem; display:inline-flex; align-items:center; justify-content:center; border-radius:50%; background:linear-gradient(135deg,#EAF8EF,#EAF3FF); border:1px solid #C7DDF4; }}

    .tag-ok,.tag-warn,.tag-danger,.tag-info {{ display:inline-block; padding:.25rem .64rem; border-radius:999px; font-size:.78rem; font-weight:800; }}
    .tag-ok {{ background:#DCFCE7; color:#166534; }}
    .tag-warn {{ background:#FEF3C7; color:#92400E; }}
    .tag-danger {{ background:#FEE2E2; color:#991B1B; }}
    .tag-info {{ background:#EAF3FF; color:{AZUL_INCAUCA}; }}
    .provicheck-footer {{ margin-top:2rem; padding:.9rem 1rem; border-top:1px solid {COLOR_BORDE}; color:{COLOR_TEXTO_SUAVE}; text-align:center; font-size:.82rem; }}
    .stAlert {{ border-radius:12px!important; }}
    [data-testid="stDataFrame"] {{ border:1px solid {COLOR_BORDE}; border-radius:12px; overflow:hidden; }}
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


def sidebar_pro():
    usuario = html.escape(str(st.session_state.get('usuario', '')))
    rol = html.escape(str(st.session_state.get('rol', 'Administrador')))
    with st.sidebar:
        st.markdown(f'''
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">🛡️ PROVICHECK</div>
            <div class="sidebar-brand-subtitle">Enterprise · {html.escape(str(VERSION))}</div>
        </div>
        ''', unsafe_allow_html=True)
        st.page_link('app.py', label='🏠 Dashboard')
        st.page_link('pages/01_Equipos.py', label='🧪 Equipos')
        st.page_link('pages/02_Hoja_de_Vida.py', label='📘 Hoja de Vida')
        st.page_link('pages/03_Administracion.py', label='⚙️ Administración')
        st.page_link('pages/04_Verificaciones.py', label='✅ Verificaciones')
        st.divider()
        st.markdown(f'''
        <div class="sidebar-user">
            <strong>👤 Usuario: {usuario or 'sin sesión'}</strong><br>
            <span>Rol: {rol}</span><br><span>🟢 En línea</span>
        </div>
        ''', unsafe_allow_html=True)
        st.divider()
        if st.button('↪ Cerrar sesión', width='stretch'):
            st.session_state['autenticado'] = False
            st.rerun()


def login_limpio():
    with st.container(border=True):
        st.markdown('### 🔐 Ingreso al sistema')
        usuario = st.text_input('Usuario')
        clave = st.text_input('Contraseña', type='password')
        entrar = st.button('Ingresar a PROVICHECK', width='stretch')
        if entrar:
            if usuario.strip() and clave.strip():
                st.session_state['autenticado'] = True
                st.session_state['usuario'] = usuario.strip()
                st.session_state.setdefault('rol', 'Administrador')
                st.rerun()
            else:
                st.warning('Ingrese usuario y contraseña.')


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
