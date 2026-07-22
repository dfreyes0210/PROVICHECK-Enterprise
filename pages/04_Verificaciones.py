from datetime import datetime

import streamlit as st

from utils.ui import (
    aplicar_estilo,
    encabezado,
    pie_pagina,
    sidebar_pro,
)
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
    initial_sidebar_state="expanded",
)

aplicar_estilo()

if not st.session_state.get("autenticado", False):
    st.warning("La sesión no está activa. Ingrese nuevamente desde el Dashboard.")
    st.page_link("app.py", label="🔐 Ir al inicio de sesión")
    st.stop()

sidebar_pro()
encabezado()

st.markdown("## ✅ Motor inteligente de verificación")
st.caption(
    "Registre los resultados observados, documente novedades y guarde "
    "la sesión completa en la base de datos SQLite."
)

DECIMALES = 4


def numero_seguro(valor):
    """Convierte valores de Excel/SQLite a float sin generar errores."""
    try:
        if valor is None or str(valor).strip() == "":
            return None
        numero = float(valor)
        if numero != numero:
            return None
        return numero
    except (TypeError, ValueError):
        return None


def obtener_limites_reales(fila_original, punto_preparado):
    """
    Obtiene límites absolutos.

    Prioridad:
    1. limite_inferior_g / limite_superior_g de la fuente.
    2. limite_inferior / limite_superior de la fuente.
    3. valor nominal ± desviacion_aceptada_g.
    """
    nominal = numero_seguro(
        fila_original.get(
            "valor_nominal_g",
            fila_original.get(
                "valor_nominal",
                punto_preparado.get("valor_nominal"),
            ),
        )
    )

    limite_inferior = numero_seguro(
        fila_original.get(
            "limite_inferior_g",
            fila_original.get("limite_inferior"),
        )
    )
    limite_superior = numero_seguro(
        fila_original.get(
            "limite_superior_g",
            fila_original.get("limite_superior"),
        )
    )

    desviacion = numero_seguro(
        fila_original.get(
            "desviacion_aceptada_g",
            fila_original.get("desviacion_aceptada"),
        )
    )

    if nominal is not None and desviacion is not None:
        if limite_inferior is None:
            limite_inferior = nominal - desviacion
        if limite_superior is None:
            limite_superior = nominal + desviacion

    return nominal, limite_inferior, limite_superior


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

equipos = equipos.copy()
equipos.columns = [str(columna).strip() for columna in equipos.columns]

puntos = puntos.copy()
puntos.columns = [str(columna).strip() for columna in puntos.columns]

# Normaliza los nombres de las columnas de la hoja maestra.
# En PROVICHECK_Base_Datos los límites y el valor nominal están
# identificados con el sufijo "_g".
alias_columnas = {
    "limite_inferior_g": "limite_inferior",
    "valor_nominal_g": "valor_nominal",
    "limite_superior_g": "limite_superior",
    "desviacion_aceptada_g": "desviacion_aceptada",
}

for columna_origen, columna_destino in alias_columnas.items():
    if columna_origen in puntos.columns and columna_destino not in puntos.columns:
        puntos[columna_destino] = puntos[columna_origen]

columnas_requeridas = {"codigo_equipo", "nombre_equipo"}
faltantes = columnas_requeridas.difference(equipos.columns)

if faltantes:
    st.error(
        "La hoja Equipos no contiene las columnas requeridas: "
        + ", ".join(sorted(faltantes))
    )
    st.stop()

equipos["descripcion"] = (
    equipos["codigo_equipo"].astype(str).str.strip()
    + " · "
    + equipos["nombre_equipo"].astype(str).str.strip()
)

st.markdown("### 1. Selección del equipo")

col_equipo, col_vista = st.columns([3, 1])

with col_equipo:
    equipo_sel = st.selectbox(
        "Seleccione el equipo que desea verificar",
        equipos["descripcion"].tolist(),
    )

with col_vista:
    tarjetas_por_fila = st.selectbox(
        "Tarjetas por fila",
        [2, 1, 3],
        index=0,
    )

codigo_equipo = equipo_sel.split(" · ", 1)[0].strip()

coincidencias = equipos[
    equipos["codigo_equipo"].astype(str).str.strip() == codigo_equipo
]

if coincidencias.empty:
    st.error("No fue posible localizar la información del equipo seleccionado.")
    st.stop()

equipo_info = coincidencias.iloc[0].to_dict()

st.markdown("### 2. Identificación del equipo")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Código", equipo_info.get("codigo_equipo", ""))
c2.metric("Estado", equipo_info.get("estado", "Sin estado"))
c3.metric("Laboratorio", equipo_info.get("laboratorio", "Sin laboratorio"))
c4.metric("Responsable", equipo_info.get("responsable", "Sin responsable"))

with st.container(border=True):
    col_a, col_b, col_c = st.columns(3)
    col_a.write(
        f"**Equipo:** {equipo_info.get('nombre_equipo', 'Sin nombre')}"
    )
    col_b.write(
        f"**Marca / Modelo:** "
        f"{equipo_info.get('marca', 'Sin marca')} · "
        f"{equipo_info.get('modelo', 'Sin modelo')}"
    )
    col_c.write(
        f"**Ubicación:** {equipo_info.get('ubicacion', 'Sin ubicación')}"
    )

st.divider()

puntos_equipo = obtener_puntos_equipo(puntos, codigo_equipo)

if puntos_equipo.empty:
    st.warning("Este equipo no tiene puntos de verificación configurados.")
    pie_pagina()
    st.stop()

st.markdown("### 3. Puntos de verificación")
st.caption(
    f"El equipo tiene {len(puntos_equipo)} punto(s) configurado(s). "
    "Cada resultado se evalúa automáticamente frente a sus límites."
)

registros = []
columnas = st.columns(tarjetas_por_fila)

for i, (_, fila) in enumerate(puntos_equipo.iterrows()):
    fila_original = fila.to_dict()
    punto = preparar_punto_para_verificacion(fila_original)
    unidad = str(punto.get("unidad", "") or "").strip()
    id_punto = punto.get("id_punto", i)
    nombre_punto = punto.get("punto_verificacion", f"Punto {i + 1}")
    nombre_chequeo = punto.get("nombre_chequeo", "Chequeo sin nombre")

    decimales_punto = punto.get("decimales", DECIMALES)
    try:
        decimales_punto = int(decimales_punto)
    except (TypeError, ValueError):
        decimales_punto = DECIMALES

    decimales_punto = max(0, min(decimales_punto, 8))

    with columnas[i % tarjetas_por_fila]:
        with st.container(border=True):
            st.markdown(
                f'''
                <div class="verification-card-title">
                    <span class="verification-card-badge">📌</span>
                    <span>{nombre_punto} {unidad}</span>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.caption(nombre_chequeo)

            (
                valor_nominal,
                limite_inferior,
                limite_superior,
            ) = obtener_limites_reales(fila_original, punto)

            d1, d2, d3 = st.columns(3)
            d1.metric(
                "Patrón",
                f"{formatear_numero(valor_nominal, decimales_punto)} {unidad}",
            )
            d2.metric(
                "Límite inferior",
                f"{formatear_numero(limite_inferior, decimales_punto)} {unidad}",
            )
            d3.metric(
                "Límite superior",
                f"{formatear_numero(limite_superior, decimales_punto)} {unidad}",
            )

            resultado = st.number_input(
                "Resultado observado",
                key=f"resultado_{codigo_equipo}_{id_punto}_{i}",
                format=f"%.{decimales_punto}f",
            )

            observacion_tipo = st.selectbox(
                "Observación",
                OPCIONES_OBSERVACION,
                key=f"obs_tipo_{codigo_equipo}_{id_punto}_{i}",
            )

            observacion_texto = ""
            if observacion_tipo == "Otro":
                observacion_texto = st.text_area(
                    "Detalle de la observación",
                    key=f"obs_txt_{codigo_equipo}_{id_punto}_{i}",
                    placeholder="Describa la novedad encontrada.",
                )

            observacion_final = (
                observacion_texto.strip()
                if observacion_tipo == "Otro"
                else observacion_tipo
            )

            resultado_num = numero_seguro(resultado)
            error_calculado = (
                resultado_num - valor_nominal
                if resultado_num is not None and valor_nominal is not None
                else None
            )

            if (
                resultado_num is not None
                and limite_inferior is not None
                and limite_superior is not None
            ):
                cumple_calculado = (
                    limite_inferior <= resultado_num <= limite_superior
                )
            else:
                cumple_calculado = None

            evaluacion = {
                "error": error_calculado,
                "limite_inferior_real": limite_inferior,
                "limite_superior_real": limite_superior,
                "cumple": cumple_calculado,
            }

            st.write(
                f"**Error calculado:** "
                f"{formatear_numero(evaluacion.get('error'), decimales_punto)} "
                f"{unidad}"
            )
            st.write(
                f"**Intervalo real:** "
                f"{formatear_numero(evaluacion.get('limite_inferior_real'), decimales_punto)} "
                f"a "
                f"{formatear_numero(evaluacion.get('limite_superior_real'), decimales_punto)} "
                f"{unidad}"
            )

            if observacion_tipo != "Sin novedades":
                estado_punto = "No evaluado"
                st.warning("🟡 NO EVALUADO · Existe una novedad registrada")
            elif evaluacion.get("cumple") is True:
                estado_punto = "Cumple"
                st.success("🟢 CUMPLE")
            elif evaluacion.get("cumple") is False:
                estado_punto = "No cumple"
                st.error("🔴 NO CUMPLE")
            else:
                estado_punto = "No evaluado"
                st.warning("🟡 SIN EVALUACIÓN O SIN LÍMITES")

            registros.append(
                {
                    "codigo_equipo": codigo_equipo,
                    "punto": nombre_punto,
                    "nombre_chequeo": nombre_chequeo,
                    "valor_nominal": valor_nominal,
                    "resultado": resultado,
                    "error": evaluacion.get("error"),
                    "limite_inferior": evaluacion.get(
                        "limite_inferior_real"
                    ),
                    "limite_superior": evaluacion.get(
                        "limite_superior_real"
                    ),
                    "estado_punto": estado_punto,
                    "observacion": observacion_final,
                }
            )

st.divider()
st.markdown("### 4. Resumen de la sesión")

total = len(registros)
cumplen = sum(
    1 for registro in registros
    if registro["estado_punto"] == "Cumple"
)
no_cumplen = sum(
    1 for registro in registros
    if registro["estado_punto"] == "No cumple"
)
no_evaluados = sum(
    1 for registro in registros
    if registro["estado_punto"] == "No evaluado"
)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Puntos configurados", total)
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

if estado_sesion == "Conforme":
    st.success("### 🟢 Estado de la sesión: CONFORME")
elif estado_sesion == "No conforme":
    st.error("### 🔴 Estado de la sesión: NO CONFORME")
else:
    st.warning("### 🟡 Estado de la sesión: INCOMPLETA")

with st.container(border=True):
    st.markdown("### 🧠 Diagnóstico automático")
    st.write(diagnostico)

st.markdown("### 5. Guardar verificación")

confirmar = st.checkbox(
    "Confirmo que revisé los resultados y las observaciones registradas."
)

guardar = st.button(
    "💾 Guardar verificación en SQLite",
    width="stretch",
    disabled=not confirmar,
)

if guardar:
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
            st.write(
                f"**Equipo:** {codigo_equipo} · "
                f"{equipo_info.get('nombre_equipo', '')}"
            )
            st.write(f"**Fecha:** {sesion['fecha']} {sesion['hora']}")
            st.write(f"**Responsable:** {sesion['responsable']}")
            st.write(f"**Estado general:** {estado_sesion}")

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Puntos", total)
            f2.metric("Cumplen", cumplen)
            f3.metric("No cumplen", no_cumplen)
            f4.metric("No evaluados", no_evaluados)

            st.markdown("### 🧠 Diagnóstico")
            st.write(diagnostico)
    else:
        st.error(mensaje)

pie_pagina()