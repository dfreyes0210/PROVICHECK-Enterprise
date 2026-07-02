import streamlit as st

from utils.ui import aplicar_estilo, encabezado
from utils.data import cargar_hoja
from utils.cards import mostrar_card_verificacion
from utils.verificacion_engine import (
    obtener_puntos_equipo,
    preparar_punto_para_verificacion,
    evaluar_resultado,
)

st.set_page_config(
    page_title="Verificaciones - PROVICHECK",
    page_icon="✅",
    layout="wide",
)

aplicar_estilo()
encabezado()

st.title("✅ Motor Inteligente de Verificación")
st.caption(
    "El analista ingresa solo el resultado observado. "
    "PROVICHECK evalúa automáticamente el cumplimiento."
)

DECIMALES = 4

equipos = cargar_hoja("Equipos")
puntos = cargar_hoja("Puntos_Verificacion")

if equipos.empty:
    st.error("No se encontró la hoja Equipos.")
    st.stop()

if puntos.empty:
    st.error("No se encontró la hoja Puntos_Verificacion.")
    st.stop()

equipos["descripcion"] = (
    equipos["codigo_equipo"].astype(str)
    + " · "
    + equipos["nombre_equipo"].astype(str)
)

equipo_sel = st.selectbox(
    "Seleccione equipo",
    equipos["descripcion"].tolist(),
)

codigo_equipo = equipo_sel.split(" · ")[0]

equipo_info = equipos[
    equipos["codigo_equipo"].astype(str) == str(codigo_equipo)
].iloc[0].to_dict()

st.divider()

c1, c2, c3 = st.columns(3)
c1.metric("Equipo", equipo_info.get("codigo_equipo", ""))
c2.metric("Estado", equipo_info.get("estado", ""))
c3.metric("Responsable", equipo_info.get("responsable", ""))

st.divider()

puntos_equipo = obtener_puntos_equipo(puntos, codigo_equipo)

if puntos_equipo.empty:
    st.warning("Este equipo no tiene puntos de verificación configurados.")
    st.stop()

st.subheader("Puntos de verificación")

tarjetas_por_fila = 2
columnas = st.columns(tarjetas_por_fila)

for i, (_, fila) in enumerate(puntos_equipo.iterrows()):
    punto = preparar_punto_para_verificacion(fila.to_dict())

    resultado_actual = st.session_state.get(
        f"resultado_{punto['id_punto']}",
        None,
    )

    evaluacion = evaluar_resultado(
        resultado_actual,
        punto["valor_nominal"],
        punto["limite_inferior"],
        punto["limite_superior"],
    )

    with columnas[i % tarjetas_por_fila]:
        resultado = mostrar_card_verificacion(
            punto=punto,
            evaluacion=evaluacion,
            resultado_key=f"resultado_{punto['id_punto']}",
            decimales=DECIMALES,
        )

        evaluacion_actualizada = evaluar_resultado(
            resultado,
            punto["valor_nominal"],
            punto["limite_inferior"],
            punto["limite_superior"],
        )

        if evaluacion_actualizada["cumple"] is True:
            st.success("🟢 Resultado dentro de límites.")
        elif evaluacion_actualizada["cumple"] is False:
            st.error("🔴 Resultado fuera de límites.")
        else:
            st.warning("🟡 Punto sin límites configurados.")

st.divider()
st.info(
    "Siguiente etapa: agregar el botón Guardar Verificación "
    "para registrar los resultados en la base de datos."
)