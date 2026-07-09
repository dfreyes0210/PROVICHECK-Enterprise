from datetime import datetime
import streamlit as st

from utils.ui import aplicar_estilo, encabezado
from utils.data import cargar_hoja
from utils.formatos import formatear_numero
from utils.persistencia import generar_id_sesion, guardar_sesion_sqlite
from utils.diagnostico import generar_diagnostico_sesion
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
    "Ingrese resultados observados, registre observaciones "
    "y guarde la sesión completa en SQLite."
)

DECIMALES = 4

OPCIONES_OBSERVACION = [
    "Sin novedades",
    "Patrón en calibración",
    "Patrón no disponible",
    "Patrón vencido",
    "Equipo inestable",
    "Equipo fuera de servicio",
    "Mantenimiento",
    "No aplica",
    "Otro",
]

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

equipo_sel = st.selectbox("Seleccione equipo", equipos["descripcion"].tolist())
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

registros = []
tarjetas_por_fila = 2
columnas = st.columns(tarjetas_por_fila)

for i, (_, fila) in enumerate(puntos_equipo.iterrows()):
    punto = preparar_punto_para_verificacion(fila.to_dict())
    unidad = punto.get("unidad", "")

    with columnas[i % tarjetas_por_fila]:
        with st.container(border=True):
            st.markdown(f"### 📌 {punto['punto_verificacion']} {unidad}")
            st.caption(punto["nombre_chequeo"])

            resultado = st.number_input(
                "Resultado observado",
                key=f"resultado_{punto['id_punto']}",
                format=f"%.{DECIMALES}f",
            )

            observacion_tipo = st.selectbox(
                "Observación",
                OPCIONES_OBSERVACION,
                key=f"obs_tipo_{punto['id_punto']}",
            )

            observacion_texto = ""
            if observacion_tipo == "Otro":
                observacion_texto = st.text_area(
                    "Detalle de observación",
                    key=f"obs_txt_{punto['id_punto']}",
                )

            observacion_final = (
                observacion_texto if observacion_tipo == "Otro" else observacion_tipo
            )

            evaluacion = evaluar_resultado(
                resultado,
                punto["valor_nominal"],
                punto["limite_inferior"],
                punto["limite_superior"],
            )

            st.write(
                f"**Valor nominal:** "
                f"{formatear_numero(punto['valor_nominal'], DECIMALES)} {unidad}"
            )
            st.write(
                f"**Error:** "
                f"{formatear_numero(evaluacion['error'], DECIMALES)} {unidad}"
            )
            st.write(
                f"**Límites reales:** "
                f"{formatear_numero(evaluacion['limite_inferior_real'], DECIMALES)} "
                f"a {formatear_numero(evaluacion['limite_superior_real'], DECIMALES)} {unidad}"
            )

            if observacion_tipo != "Sin novedades":
                estado_punto = "No evaluado"
                st.warning("🟡 NO EVALUADO")
            elif evaluacion["cumple"] is True:
                estado_punto = "Cumple"
                st.success("🟢 CUMPLE")
            elif evaluacion["cumple"] is False:
                estado_punto = "No cumple"
                st.error("🔴 NO CUMPLE")
            else:
                estado_punto = "No evaluado"
                st.warning("🟡 SIN EVALUACIÓN / SIN LÍMITES")

            registros.append(
                {
                    "codigo_equipo": codigo_equipo,
                    "punto": punto.get("punto_verificacion", ""),
                    "nombre_chequeo": punto.get("nombre_chequeo", ""),
                    "valor_nominal": punto.get("valor_nominal", None),
                    "resultado": resultado,
                    "error": evaluacion.get("error", None),
                    "limite_inferior": evaluacion.get("limite_inferior_real", None),
                    "limite_superior": evaluacion.get("limite_superior_real", None),
                    "estado_punto": estado_punto,
                    "observacion": observacion_final,
                }
            )

st.divider()

total = len(registros)
cumplen = sum(1 for r in registros if r["estado_punto"] == "Cumple")
no_cumplen = sum(1 for r in registros if r["estado_punto"] == "No cumple")
no_evaluados = sum(1 for r in registros if r["estado_punto"] == "No evaluado")

r1, r2, r3, r4 = st.columns(4)
r1.metric("Puntos", total)
r2.metric("Cumplen", cumplen)
r3.metric("No cumplen", no_cumplen)
r4.metric("No evaluados", no_evaluados)

if no_cumplen > 0:
    estado_sesion = "No conforme"
elif no_evaluados > 0:
    estado_sesion = "Incompleta"
else:
    estado_sesion = "Conforme"

diagnostico = generar_diagnostico_sesion(
    estado_sesion,
    total,
    cumplen,
    no_cumplen,
    no_evaluados,
)

st.markdown(f"### Estado de la sesión: **{estado_sesion}**")

with st.container(border=True):
    st.markdown("### 🧠 Diagnóstico automático")
    st.write(diagnostico)

if st.button("💾 Guardar Verificación en SQLite", use_container_width=True):
    id_sesion = generar_id_sesion(codigo_equipo)
    fecha_hora = datetime.now()

    sesion = {
        "id_sesion": id_sesion,
        "codigo_equipo": codigo_equipo,
        "nombre_equipo": equipo_info.get("nombre_equipo", ""),
        "laboratorio": equipo_info.get("laboratorio", ""),
        "fecha": fecha_hora.date().isoformat(),
        "hora": fecha_hora.time().strftime("%H:%M:%S"),
        "responsable": equipo_info.get("responsable", ""),
        "estado": estado_sesion,
        "total_puntos": total,
        "puntos_cumplen": cumplen,
        "puntos_no_cumplen": no_cumplen,
        "puntos_no_evaluados": no_evaluados,
    }

    ok, mensaje = guardar_sesion_sqlite(sesion, registros)

    if ok:
        st.success(f"✅ {mensaje}")

        with st.container(border=True):
            st.markdown("## ✅ Sesión finalizada")
            st.write(f"**Sesión:** {id_sesion}")
            st.write(f"**Equipo:** {codigo_equipo} · {equipo_info.get('nombre_equipo', '')}")
            st.write(f"**Fecha:** {sesion['fecha']} {sesion['hora']}")
            st.write(f"**Responsable:** {sesion['responsable']}")
            st.write(f"**Estado general:** {estado_sesion}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Puntos", total)
            c2.metric("Cumplen", cumplen)
            c3.metric("No cumplen", no_cumplen)
            c4.metric("No evaluados", no_evaluados)

            st.markdown("### 🧠 Diagnóstico")
            st.write(diagnostico)

    else:
        st.error(mensaje)