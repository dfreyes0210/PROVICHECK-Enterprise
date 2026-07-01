import streamlit as st

from utils.ui import aplicar_estilo, encabezado
from utils.data import cargar_hoja
from utils.formatos import formatear_numero
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

for i, (_, fila) in enumerate(puntos_equipo.iterrows()):
    punto = preparar_punto_para_verificacion(fila.to_dict())

    with st.expander(
        f"📌 {punto['punto_verificacion']} · {punto['nombre_chequeo']}",
        expanded=i == 0,
    ):
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Valor nominal",
            formatear_numero(punto["valor_nominal"], DECIMALES),
        )
        col2.metric(
            "Tolerancia inferior",
            formatear_numero(punto["limite_inferior"], DECIMALES),
        )
        col3.metric(
            "Tolerancia superior",
            formatear_numero(punto["limite_superior"], DECIMALES),
        )
        col4.metric("Unidad", punto["unidad"])

        resultado = st.number_input(
            f"Resultado observado - {punto['punto_verificacion']}",
            key=f"resultado_{punto['id_punto']}",
            format=f"%.{DECIMALES}f",
        )

        evaluacion = evaluar_resultado(
            resultado,
            punto["valor_nominal"],
            punto["limite_inferior"],
            punto["limite_superior"],
        )

        st.write(
            f"**Resultado observado:** "
            f"{formatear_numero(evaluacion['resultado'], DECIMALES)} {punto['unidad']}"
        )
        st.write(
            f"**Valor nominal:** "
            f"{formatear_numero(evaluacion['valor_nominal'], DECIMALES)} {punto['unidad']}"
        )
        st.write(
            f"**Error:** "
            f"{formatear_numero(evaluacion['error'], DECIMALES)} {punto['unidad']}"
        )
        st.write(
            f"**Límite inferior real:** "
            f"{formatear_numero(evaluacion['limite_inferior_real'], DECIMALES)} {punto['unidad']}"
        )
        st.write(
            f"**Límite superior real:** "
            f"{formatear_numero(evaluacion['limite_superior_real'], DECIMALES)} {punto['unidad']}"
        )
        st.write(f"**Evaluación:** {evaluacion['mensaje']}")

        if evaluacion["cumple"] is True:
            st.success("🟢 CUMPLE")
        elif evaluacion["cumple"] is False:
            st.error("🔴 NO CUMPLE")
        else:
            st.warning("🟡 SIN EVALUACIÓN")

st.divider()
st.info(
    "En la siguiente etapa agregaremos el botón Guardar Verificación "
    "para registrar los resultados en la base de datos."
)