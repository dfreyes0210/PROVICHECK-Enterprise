import streamlit as st
from utils.ui import aplicar_estilo, encabezado, tarjeta_equipo
from utils.data import cargar_hoja

st.set_page_config(page_title="Equipos - PROVICHECK", page_icon="🧪", layout="wide")
aplicar_estilo(); encabezado()
st.title("🧪 Equipos")
st.caption("Gestión visual inicial de equipos registrados en la base maestra.")

equipos = cargar_hoja("Equipos")
if equipos.empty:
    st.error("No se encontró información en la hoja Equipos.")
    st.stop()

busqueda = st.text_input("Buscar equipo por código, nombre, marca, modelo o responsable")
df = equipos.copy()
if busqueda:
    mask = df.astype(str).apply(lambda col: col.str.contains(busqueda, case=False, na=False)).any(axis=1)
    df = df[mask]
if "laboratorio" in df.columns:
    labs = ["Todos"] + sorted(df["laboratorio"].dropna().astype(str).unique().tolist())
    lab = st.selectbox("Filtrar por laboratorio", labs)
    if lab != "Todos":
        df = df[df["laboratorio"].astype(str) == lab]

st.write(f"Equipos encontrados: **{len(df)}**")
cols = st.columns(3)
for i, (_, row) in enumerate(df.iterrows()):
    with cols[i % 3]:
        tarjeta_equipo(row.to_dict())
        if st.button(f"Abrir hoja de vida {row.get('codigo_equipo','')}", key=f"btn_{i}"):
            st.session_state["equipo_seleccionado"] = row.to_dict()
            st.switch_page("pages/02_Hoja_de_Vida.py")
