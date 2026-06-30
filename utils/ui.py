import streamlit as st
from config import APP_NAME, APP_SUBTITLE, VERSION

def aplicar_estilo():
    st.markdown("""
    <style>
    .main-header {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(120deg, #003B73, #005BBB, #2E8BC0); color: white; margin-bottom: 1.2rem; box-shadow: 0 6px 18px rgba(0,0,0,0.12);}
    .main-header h1 {margin: 0; font-size: 2.1rem; letter-spacing: 0.5px;}
    .main-header p {margin: 0.25rem 0 0 0; opacity: 0.95; font-size: 1rem;}
    .equipment-card {padding: 1rem; border-radius: 16px; background: white; border: 1px solid #E5E7EB; box-shadow: 0 3px 12px rgba(0,0,0,0.05); min-height: 210px; margin-bottom: 0.8rem;}
    .tag-ok {background: #DCFCE7; color: #166534; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
    .tag-warn {background: #FEF3C7; color: #92400E; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
    .tag-danger {background: #FEE2E2; color: #991B1B; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
    </style>
    """, unsafe_allow_html=True)

def encabezado():
    st.markdown(f"""
    <div class="main-header">
        <h1>🧪 {APP_NAME}</h1>
        <p>{APP_SUBTITLE} · {VERSION}</p>
        <p><strong>La confianza en un laboratorio comienza con la confianza en sus equipos.</strong></p>
    </div>
    """, unsafe_allow_html=True)

def login_limpio():
    st.markdown("### Ingreso al sistema")
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    entrar = st.button("Ingresar", use_container_width=True)
    if entrar:
        if usuario.strip() and clave.strip():
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario.strip()
            st.rerun()
        else:
            st.warning("Ingrese usuario y contraseña.")

def tarjeta_equipo(equipo: dict):
    codigo = equipo.get("codigo_equipo", "Sin código")
    nombre = equipo.get("nombre_equipo", "Equipo sin nombre")
    laboratorio = equipo.get("laboratorio", "Sin laboratorio")
    estado = str(equipo.get("estado", "Sin estado"))
    responsable = equipo.get("responsable", "Sin responsable")
    criticidad = equipo.get("criticidad", "Sin criticidad")
    tag_class = "tag-ok"
    if "fuera" in estado.lower() or "inactivo" in estado.lower():
        tag_class = "tag-danger"
    elif "mantenimiento" in estado.lower() or "observ" in estado.lower():
        tag_class = "tag-warn"
    st.markdown(f"""
    <div class="equipment-card">
        <h3>{codigo}</h3><p><strong>{nombre}</strong></p>
        <p>🏭 Laboratorio: {laboratorio}</p><p>👤 Responsable: {responsable}</p>
        <p>⚠️ Criticidad: {criticidad}</p><p><span class="{tag_class}">{estado}</span></p>
    </div>
    """, unsafe_allow_html=True)
def estado_class(estado: str):
    txt = str(estado).lower()

    if "fuera" in txt or "inactivo" in txt or "baja" in txt:
        return "tag-danger"

    if "mant" in txt or "calibr" in txt or "observ" in txt:
        return "tag-warn"

    return "tag-ok"


def tarjeta_equipo_html(equipo: dict):
    codigo = equipo.get("codigo_equipo", "Sin código")
    nombre = equipo.get("nombre_equipo", "Equipo sin nombre")
    laboratorio = equipo.get("laboratorio", "Sin laboratorio")
    ubicacion = equipo.get("ubicacion", "Sin ubicación")
    estado = equipo.get("estado", "Sin estado")
    responsable = equipo.get("responsable", "Sin responsable")
    criticidad = equipo.get("criticidad", "Sin criticidad")
    marca = equipo.get("marca", "Sin marca")
    modelo = equipo.get("modelo", "Sin modelo")
    tipo = equipo.get("tipo_equipo", "Sin tipo")

    return f"""
    <div class="equipment-card">
        <div style="font-size:2.2rem;">⚖️</div>
        <div class="equipment-code">{codigo}</div>
        <div class="equipment-name">{nombre}</div>
        <div class="equipment-line">🏭 <strong>Laboratorio:</strong> {laboratorio}</div>
        <div class="equipment-line">📍 <strong>Ubicación:</strong> {ubicacion}</div>
        <div class="equipment-line">🏷️ <strong>Tipo:</strong> {tipo}</div>
        <div class="equipment-line">🔧 <strong>Marca/Modelo:</strong> {marca} · {modelo}</div>
        <div class="equipment-line">👤 <strong>Responsable:</strong> {responsable}</div>
        <div class="equipment-line">⚠️ <strong>Criticidad:</strong> {criticidad}</div>
        <p><span class="{estado_class(estado)}">{estado}</span></p>
    </div>
    """