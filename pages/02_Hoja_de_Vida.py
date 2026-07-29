from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import crear_base_datos

from utils.ui import (
    aplicar_estilo,
    encabezado,
    requerir_autenticacion,
    sidebar_pro,
)
from utils.formatos import formatear_numero
from utils.data import cargar_hoja
from utils.reportes_pdf import generar_informe_tendencia_pdf
from utils.documentos import (
    actualizar_estados_documentos,
    eliminar_documento,
    leer_documento,
    registrar_documento,
)
from utils.calibraciones import (
    ESTADOS_RESULTADO,
    TIPOS_CALIBRACION,
    dias_para_vencimiento,
    eliminar_calibracion,
    listar_calibraciones,
    registrar_calibracion,
    resumen_calibraciones,
)
from utils.mantenimientos import (
    ESTADOS_MANTENIMIENTO,
    RESULTADOS_MANTENIMIENTO,
    TIPOS_EJECUTOR,
    TIPOS_MANTENIMIENTO,
    eliminar_mantenimiento,
    listar_mantenimientos,
    registrar_mantenimiento,
    resumen_mantenimientos,
)
from utils.sqlite_consultas import (
    consultar_ultima_verificacion,
    consultar_historial_equipo,
    consultar_eventos_equipo,
    consultar_detalle_sesion,
    consultar_documentos_equipo,
)


st.set_page_config(
    page_title="Hoja de Vida Enterprise - PROVICHECK",
    page_icon="📘",
    layout="wide",
)

crear_base_datos()

aplicar_estilo()
requerir_autenticacion()
sidebar_pro()
encabezado()



def estado_visual(estado):
    estado_txt = str(estado).lower()

    if "conforme" in estado_txt and "no" not in estado_txt:
        return "🟢 Conforme"

    if "no conforme" in estado_txt:
        return "🔴 No conforme"

    if "incompleta" in estado_txt:
        return "🟡 Incompleta"

    if "cumple" in estado_txt:
        return "🟢 Cumple"

    if "no cumple" in estado_txt:
        return "🔴 No cumple"

    return f"⚪ {estado}"



def texto_seguro(valor, por_defecto="No registrado"):
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def normalizar_codigo(valor):
    texto = texto_seguro(valor, "")
    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base
    return texto


def convertir_fecha(valor):
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        return None
    return fecha.date()


def buscar_logo_providencia():
    candidatos = [
        Path("assets/logo_providencia.png"),
        Path("logo_providencia.png"),
        Path(__file__).resolve().parent.parent / "assets" / "logo_providencia.png",
    ]

    for candidato in candidatos:
        if candidato.exists():
            return candidato

    return None


def cargar_catalogo_patrones():
    puntos_catalogo = cargar_hoja("Puntos_Verificacion")
    patrones_catalogo = cargar_hoja("Equipos_Patrones")

    if not puntos_catalogo.empty:
        puntos_catalogo = puntos_catalogo.copy()
        puntos_catalogo.columns = [
            str(columna).strip()
            for columna in puntos_catalogo.columns
        ]

    if not patrones_catalogo.empty:
        patrones_catalogo = patrones_catalogo.copy()
        patrones_catalogo.columns = [
            str(columna).strip()
            for columna in patrones_catalogo.columns
        ]

    return puntos_catalogo, patrones_catalogo


def preparar_patrones_equipo(codigo_equipo):
    puntos_catalogo, patrones_catalogo = cargar_catalogo_patrones()

    if puntos_catalogo.empty:
        return pd.DataFrame()

    codigo_normalizado = normalizar_codigo(codigo_equipo)
    puntos_catalogo["codigo_equipo_normalizado"] = (
        puntos_catalogo["codigo_equipo"]
        .apply(normalizar_codigo)
    )

    puntos_equipo_catalogo = puntos_catalogo[
        puntos_catalogo["codigo_equipo_normalizado"]
        == codigo_normalizado
    ].copy()

    if puntos_equipo_catalogo.empty:
        return pd.DataFrame()

    puntos_equipo_catalogo["codigo_patron"] = (
        puntos_equipo_catalogo["codigo_patron"]
        .apply(normalizar_codigo)
    )

    if patrones_catalogo.empty:
        return puntos_equipo_catalogo

    patrones_catalogo["codigo_patron"] = (
        patrones_catalogo["codigo_patron"]
        .apply(normalizar_codigo)
    )

    columnas_patron = [
        columna
        for columna in [
            "codigo_patron",
            "descripcion",
            "marca",
            "valor_nominal_g",
            "unidad",
            "fecha_vencimiento_calibracion",
            "estado",
            "observaciones",
        ]
        if columna in patrones_catalogo.columns
    ]

    return puntos_equipo_catalogo.merge(
        patrones_catalogo[columnas_patron],
        on="codigo_patron",
        how="left",
        suffixes=("_punto", "_patron"),
    )


def crear_figura_tendencia(df_punto, punto_sel, unidad):
    figura = go.Figure()

    figura.add_trace(
        go.Scatter(
            x=df_punto["fecha_hora"],
            y=df_punto["resultado"],
            mode="lines+markers",
            name="Resultado observado",
            customdata=df_punto[
                ["responsable", "estado_punto", "observacion"]
            ].fillna("").to_numpy(),
            hovertemplate=(
                "<b>%{x|%d/%m/%Y %H:%M}</b><br>"
                "Resultado: %{y}<br>"
                "Responsable: %{customdata[0]}<br>"
                "Estado: %{customdata[1]}<br>"
                "Observación: %{customdata[2]}"
                "<extra></extra>"
            ),
        )
    )

    figura.add_trace(
        go.Scatter(
            x=df_punto["fecha_hora"],
            y=df_punto["valor_nominal"],
            mode="lines",
            name="Valor nominal",
        )
    )

    figura.add_trace(
        go.Scatter(
            x=df_punto["fecha_hora"],
            y=df_punto["limite_superior"],
            mode="lines",
            line={"dash": "dash"},
            name="Límite superior",
        )
    )

    figura.add_trace(
        go.Scatter(
            x=df_punto["fecha_hora"],
            y=df_punto["limite_inferior"],
            mode="lines",
            line={"dash": "dash"},
            name="Límite inferior",
        )
    )

    fuera_tolerancia = df_punto[
        df_punto["estado_punto"].astype(str).str.lower()
        == "no cumple"
    ]

    if not fuera_tolerancia.empty:
        figura.add_trace(
            go.Scatter(
                x=fuera_tolerancia["fecha_hora"],
                y=fuera_tolerancia["resultado"],
                mode="markers",
                marker={"size": 12, "symbol": "x"},
                name="Fuera de tolerancia",
            )
        )

    figura.update_layout(
        height=520,
        title=f"Tendencia histórica - {punto_sel}",
        xaxis_title="Fecha y hora",
        yaxis_title=f"Resultado ({unidad})" if unidad else "Resultado",
        legend_title="Serie",
        hovermode="x unified",
        margin={"l": 40, "r": 25, "t": 65, "b": 45},
    )

    return figura


def calcular_resumen_tendencia(df_punto):
    resultados = pd.to_numeric(
        df_punto["resultado"],
        errors="coerce",
    ).dropna()
    errores = pd.to_numeric(
        df_punto["error"],
        errors="coerce",
    ).dropna()

    total = len(df_punto)
    conformes = int(
        df_punto["estado_punto"]
        .astype(str)
        .str.lower()
        .eq("cumple")
        .sum()
    )
    no_conformes = int(
        df_punto["estado_punto"]
        .astype(str)
        .str.lower()
        .eq("no cumple")
        .sum()
    )
    no_evaluados = int(
        df_punto["estado_punto"]
        .astype(str)
        .str.lower()
        .eq("no evaluado")
        .sum()
    )

    return {
        "total": total,
        "promedio": resultados.mean() if not resultados.empty else None,
        "desviacion": (
            resultados.std(ddof=1)
            if len(resultados) > 1
            else 0.0
        ),
        "minimo": resultados.min() if not resultados.empty else None,
        "maximo": resultados.max() if not resultados.empty else None,
        "error_promedio": errores.mean() if not errores.empty else None,
        "conformes": conformes,
        "no_conformes": no_conformes,
        "no_evaluados": no_evaluados,
        "cumplimiento": (
            conformes / total * 100
            if total
            else 0.0
        ),
    }


equipo = st.session_state.get("equipo_seleccionado")

if not equipo:
    st.warning("Seleccione primero un equipo desde el módulo Equipos.")
    st.page_link("pages/01_Equipos.py", label="🧪 Ir a Equipos")
    st.stop()

codigo = str(equipo.get("codigo_equipo", "Sin código"))
nombre = equipo.get("nombre_equipo", "Equipo sin nombre")
estado = equipo.get("estado", "Sin estado")
criticidad = equipo.get("criticidad", "Sin criticidad")
laboratorio = equipo.get("laboratorio", "Sin laboratorio")
ubicacion = equipo.get("ubicacion", "Sin ubicación")
responsable = equipo.get("responsable", "Sin responsable")
marca = equipo.get("marca", "Sin marca")
modelo = equipo.get("modelo", "Sin modelo")
serie = equipo.get("serie", "Sin serie")
frecuencia = equipo.get("frecuencia_verificacion", "Sin frecuencia")

ultima = consultar_ultima_verificacion(codigo)
historial = consultar_historial_equipo(codigo, limite=5000)
eventos = consultar_eventos_equipo(codigo, limite=20)
actualizar_estados_documentos(codigo)
documentos = consultar_documentos_equipo(codigo)

st.title("📘 Hoja de Vida del Equipo")
st.subheader(f"{codigo} · {nombre}")

st.divider()

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    with st.container(border=True):
        st.markdown("### 📷 Equipo")
        st.info("Fotografía pendiente")
        st.info("Código QR pendiente")

with col2:
    with st.container(border=True):
        st.markdown("### Identidad técnica")
        st.write(f"**Código:** {codigo}")
        st.write(f"**Nombre:** {nombre}")
        st.write(f"**Marca:** {marca}")
        st.write(f"**Modelo:** {modelo}")
        st.write(f"**Serie:** {serie}")
        st.write(f"**Laboratorio:** {laboratorio}")
        st.write(f"**Ubicación:** {ubicacion}")
        st.write(f"**Responsable:** {responsable}")

with col3:
    with st.container(border=True):
        st.markdown("### Estado")
        st.metric("Estado", estado)
        st.metric("Criticidad", criticidad)
        st.metric("Frecuencia", frecuencia)

st.divider()

if not ultima.empty:
    ultima_fila = ultima.iloc[0]
    ultima_fecha = ultima_fila.get("fecha", "Sin fecha")
    ultima_estado = ultima_fila.get("estado", "Sin estado")
    total_verificaciones = len(historial)
    total_eventos = len(eventos)
else:
    ultima_fila = None
    ultima_fecha = "Sin registros"
    ultima_estado = "Sin registros"
    total_verificaciones = 0
    total_eventos = 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Última verificación", ultima_fecha)
k2.metric("Estado última sesión", estado_visual(ultima_estado))
k3.metric("Sesiones registradas", total_verificaciones)
k4.metric("Eventos en bitácora", total_eventos)
k5.metric("Documentos", len(documentos))

tabs = st.tabs(
    [
        "📋 Información",
        "✅ Última verificación",
        "📜 Historial",
        "📝 Bitácora",
        "📈 Tendencias",
        "🧭 Calibraciones",
        "🔧 Mantenimientos",
        "📂 Documentos",
        "🔍 Auditoría",
    ]
)

with tabs[0]:
    st.markdown("### Información técnica completa")
    df_info = pd.DataFrame([equipo]).T
    df_info.columns = ["Valor"]
    st.dataframe(df_info, width="stretch")

with tabs[1]:
    st.markdown("### Última verificación registrada")

    if ultima.empty:
        st.info("Este equipo aún no tiene verificaciones guardadas en SQLite.")
    else:
        col_a, col_b, col_c, col_d = st.columns(4)

        col_a.metric("Fecha", ultima_fila.get("fecha", ""))
        col_b.metric("Hora", ultima_fila.get("hora", ""))
        col_c.metric("Responsable", ultima_fila.get("responsable", ""))
        col_d.metric("Estado", estado_visual(ultima_fila.get("estado", "")))

        st.divider()

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Puntos", int(ultima_fila.get("total_puntos", 0)))
        r2.metric("Cumplen", int(ultima_fila.get("puntos_cumplen", 0)))
        r3.metric("No cumplen", int(ultima_fila.get("puntos_no_cumplen", 0)))
        r4.metric("No evaluados", int(ultima_fila.get("puntos_no_evaluados", 0)))

        detalle = consultar_detalle_sesion(ultima_fila.get("id_sesion"))

        st.markdown("### Detalle de la última sesión")
        if detalle.empty:
            st.info("No se encontró detalle para esta sesión.")
        else:
            st.dataframe(detalle, width="stretch", hide_index=True)

with tabs[2]:
    st.markdown("### Historial de verificaciones")

    if historial.empty:
        st.info("No hay historial registrado para este equipo.")
    else:
        st.dataframe(historial, width="stretch", hide_index=True)

        id_sesion = st.selectbox(
            "Ver detalle de sesión",
            historial["id_sesion"].tolist(),
        )

        detalle_hist = consultar_detalle_sesion(id_sesion)

        st.markdown("### Detalle seleccionado")
        st.dataframe(detalle_hist, width="stretch", hide_index=True)

with tabs[3]:
    st.markdown("### Bitácora del equipo")

    if eventos.empty:
        st.info("No hay eventos registrados en la bitácora para este equipo.")
    else:
        st.dataframe(eventos, width="stretch", hide_index=True)

with tabs[4]:
    st.markdown("### 📈 Tendencias de verificaciones")
    st.caption(
        "Seleccione el patrón y el periodo de análisis. "
        "PROVICHECK mostrará la tendencia histórica y generará "
        "un informe PDF institucional."
    )

    if historial.empty:
        st.info("Aún no hay verificaciones registradas para este equipo.")
    else:
        detalles = []

        for _, fila_sesion in historial.iterrows():
            id_sesion_actual = fila_sesion.get("id_sesion")
            df_detalle = consultar_detalle_sesion(id_sesion_actual)

            if df_detalle.empty:
                continue

            df_detalle = df_detalle.copy()
            df_detalle["id_sesion"] = id_sesion_actual
            df_detalle["fecha"] = fila_sesion.get("fecha")
            df_detalle["hora"] = fila_sesion.get("hora")
            df_detalle["responsable"] = fila_sesion.get(
                "responsable",
                "No registrado",
            )
            detalles.append(df_detalle)

        if not detalles:
            st.info("No hay detalle suficiente para construir tendencias.")
        else:
            df_tendencia = pd.concat(detalles, ignore_index=True)

            columnas_numericas = [
                "valor_nominal",
                "resultado",
                "error",
                "limite_inferior",
                "limite_superior",
            ]
            for columna in columnas_numericas:
                if columna in df_tendencia.columns:
                    df_tendencia[columna] = pd.to_numeric(
                        df_tendencia[columna],
                        errors="coerce",
                    )

            df_tendencia["fecha_hora"] = pd.to_datetime(
                df_tendencia["fecha"].astype(str)
                + " "
                + df_tendencia["hora"].astype(str),
                errors="coerce",
            )
            df_tendencia = df_tendencia.dropna(
                subset=["fecha_hora"]
            )

            patrones_equipo = preparar_patrones_equipo(codigo)

            if patrones_equipo.empty:
                st.warning(
                    "No se encontraron patrones asociados al equipo "
                    "en la base maestra."
                )
            else:
                patrones_equipo = patrones_equipo.copy()
                patrones_equipo["etiqueta_patron"] = (
                    patrones_equipo["codigo_patron"].astype(str)
                    + " · "
                    + patrones_equipo["punto_verificacion"].astype(str)
                    + " "
                    + patrones_equipo["unidad_punto"].fillna("").astype(str)
                )

                opciones_patron = (
                    patrones_equipo["etiqueta_patron"]
                    .drop_duplicates()
                    .tolist()
                )

                fechas_validas = df_tendencia["fecha_hora"].dropna()
                fecha_minima = fechas_validas.min().date()
                fecha_maxima = fechas_validas.max().date()

                f1, f2, f3 = st.columns([2.2, 1, 1])

                with f1:
                    patron_seleccionado = st.selectbox(
                        "Patrón para la tendencia",
                        opciones_patron,
                        key=f"patron_tendencia_{codigo}",
                    )

                with f2:
                    fecha_desde = st.date_input(
                        "Desde",
                        value=fecha_minima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        format="DD/MM/YYYY",
                        key=f"fecha_desde_tendencia_{codigo}",
                    )

                with f3:
                    fecha_hasta = st.date_input(
                        "Hasta",
                        value=fecha_maxima,
                        min_value=fecha_minima,
                        max_value=fecha_maxima,
                        format="DD/MM/YYYY",
                        key=f"fecha_hasta_tendencia_{codigo}",
                    )

                if fecha_desde > fecha_hasta:
                    st.error(
                        "La fecha inicial no puede ser posterior "
                        "a la fecha final."
                    )
                else:
                    patron_fila = patrones_equipo[
                        patrones_equipo["etiqueta_patron"]
                        == patron_seleccionado
                    ].iloc[0]

                    punto_sel = str(
                        patron_fila.get("punto_verificacion")
                    )
                    codigo_patron_sel = texto_seguro(
                        patron_fila.get("codigo_patron"),
                        "",
                    )
                    unidad_sel = texto_seguro(
                        patron_fila.get("unidad_punto")
                        or patron_fila.get("unidad_patron"),
                        "",
                    )

                    df_punto = df_tendencia[
                        df_tendencia["punto"].astype(str)
                        == punto_sel
                    ].copy()

                    inicio = pd.Timestamp(fecha_desde)
                    fin = (
                        pd.Timestamp(fecha_hasta)
                        + pd.Timedelta(days=1)
                        - pd.Timedelta(microseconds=1)
                    )

                    df_punto = df_punto[
                        (df_punto["fecha_hora"] >= inicio)
                        & (df_punto["fecha_hora"] <= fin)
                    ].copy()
                    df_punto = df_punto.sort_values("fecha_hora")

                    with st.container(border=True):
                        st.markdown("#### 🔬 Patrón seleccionado")
                        p1, p2, p3, p4 = st.columns(4)
                        p1.metric(
                            "Código",
                            codigo_patron_sel,
                        )
                        p2.metric(
                            "Valor nominal",
                            (
                                f"{formatear_numero(
                                    patron_fila.get(
                                        'valor_nominal_g_patron'
                                    ),
                                    4,
                                )} {unidad_sel}"
                            ),
                        )
                        p3.metric(
                            "Vencimiento",
                            texto_seguro(
                                patron_fila.get(
                                    "fecha_vencimiento_calibracion"
                                )
                            ),
                        )
                        p4.metric(
                            "Estado",
                            texto_seguro(
                                patron_fila.get("estado_patron")
                                or patron_fila.get("estado")
                            ),
                        )
                        st.caption(
                            f"{texto_seguro(patron_fila.get('descripcion'))} · "
                            f"Marca: {texto_seguro(patron_fila.get('marca'))}"
                        )

                    if df_punto.empty:
                        st.warning(
                            "No hay verificaciones para este patrón "
                            "en el periodo seleccionado."
                        )
                    else:
                        resumen = calcular_resumen_tendencia(df_punto)

                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Registros", resumen["total"])
                        m2.metric(
                            "Promedio",
                            formatear_numero(resumen["promedio"], 4),
                        )
                        m3.metric(
                            "Desviación estándar",
                            formatear_numero(
                                resumen["desviacion"],
                                4,
                            ),
                        )
                        m4.metric(
                            "Cumplimiento",
                            f"{resumen['cumplimiento']:.1f} %",
                        )

                        m5, m6, m7, m8 = st.columns(4)
                        m5.metric(
                            "Mínimo",
                            formatear_numero(resumen["minimo"], 4),
                        )
                        m6.metric(
                            "Máximo",
                            formatear_numero(resumen["maximo"], 4),
                        )
                        m7.metric(
                            "Error promedio",
                            formatear_numero(
                                resumen["error_promedio"],
                                4,
                            ),
                        )
                        m8.metric(
                            "No evaluados",
                            resumen["no_evaluados"],
                        )

                        figura = crear_figura_tendencia(
                            df_punto,
                            punto_sel,
                            unidad_sel,
                        )
                        st.plotly_chart(
                            figura,
                            width="stretch",
                        )

                        st.markdown("### Tabla de resultados")
                        columnas_tabla = [
                            "fecha",
                            "hora",
                            "resultado",
                            "error",
                            "limite_inferior",
                            "limite_superior",
                            "estado_punto",
                            "responsable",
                            "observacion",
                        ]
                        columnas_tabla = [
                            columna
                            for columna in columnas_tabla
                            if columna in df_punto.columns
                        ]

                        st.dataframe(
                            df_punto[columnas_tabla],
                            width="stretch",
                            hide_index=True,
                        )

                        informacion_patron_pdf = {
                            "codigo_patron": codigo_patron_sel,
                            "descripcion": patron_fila.get(
                                "descripcion"
                            ),
                            "marca": patron_fila.get("marca"),
                            "valor_nominal_g": patron_fila.get(
                                "valor_nominal_g_patron"
                            ),
                            "unidad": unidad_sel,
                            "fecha_vencimiento_calibracion": (
                                patron_fila.get(
                                    "fecha_vencimiento_calibracion"
                                )
                            ),
                            "estado": (
                                patron_fila.get("estado_patron")
                                or patron_fila.get("estado")
                            ),
                        }

                        usuario_emision = str(
                            st.session_state.get(
                                "nombre_usuario",
                                st.session_state.get(
                                    "usuario",
                                    responsable,
                                ),
                            )
                        )

                        try:
                            pdf_tendencia = (
                                generar_informe_tendencia_pdf(
                                    equipo=equipo,
                                    patron=informacion_patron_pdf,
                                    datos=df_punto,
                                    fecha_inicial=fecha_desde,
                                    fecha_final=fecha_hasta,
                                    usuario_emision=usuario_emision,
                                    logo_path=buscar_logo_providencia(),
                                    version_sistema="1.0",
                                )
                            )

                            nombre_pdf = (
                                "PROVICHECK_Tendencia_"
                                f"{codigo}_"
                                f"{codigo_patron_sel}_"
                                f"{fecha_desde.isoformat()}_"
                                f"{fecha_hasta.isoformat()}.pdf"
                            )

                            st.download_button(
                                "📄 Generar y descargar informe PDF",
                                data=pdf_tendencia,
                                file_name=nombre_pdf,
                                mime="application/pdf",
                                type="primary",
                                width="stretch",
                                key=(
                                    f"pdf_tendencia_{codigo}_"
                                    f"{codigo_patron_sel}"
                                ),
                            )
                        except Exception as exc:
                            st.error(
                                "No fue posible generar el informe PDF. "
                                f"Detalle: {exc}"
                            )

with tabs[5]:
    st.markdown("### 🧭 Gestión de calibraciones")
    st.caption(
        "Registro técnico, vigencia, trazabilidad metrológica "
        "y consulta histórica de las calibraciones del equipo."
    )

    resumen_cal = resumen_calibraciones(codigo)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", resumen_cal["total"])
    c2.metric("🟢 Vigentes", resumen_cal["vigentes"])
    c3.metric("🟡 Próximas", resumen_cal["proximas"])
    c4.metric("🔴 Vencidas", resumen_cal["vencidas"])
    c5.metric(
        "Días para próxima",
        resumen_cal["dias_restantes"]
        if resumen_cal["dias_restantes"] is not None
        else "—",
    )

    calibraciones = listar_calibraciones(codigo)

    if resumen_cal["vencidas"] > 0:
        st.error(
            f"Este equipo tiene {resumen_cal['vencidas']} "
            "calibración(es) vencida(s)."
        )
    elif resumen_cal["proximas"] > 0:
        st.warning(
            f"Este equipo tiene {resumen_cal['proximas']} "
            "calibración(es) próxima(s) a vencer."
        )
    elif resumen_cal["vigentes"] > 0:
        st.success(
            "La calibración vigente del equipo se encuentra "
            "dentro del periodo establecido."
        )

    st.divider()

    with st.expander(
        "➕ Registrar calibración",
        expanded=calibraciones.empty,
    ):
        documentos_cal = consultar_documentos_equipo(codigo)
        opciones_documento = {"Sin documento asociado": None}

        if not documentos_cal.empty:
            for _, doc in documentos_cal.iterrows():
                etiqueta = (
                    f"{doc.get('tipo_documento', 'Documento')} · "
                    f"{doc.get('nombre_archivo', '')}"
                )
                opciones_documento[etiqueta] = int(doc.get("id"))

        st.markdown(
            """
            <div class="pc-accreditation-box">
                <strong>🏛️ Acreditación del laboratorio</strong><br>
                <span>
                    Active la opción cuando la calibración esté cubierta
                    por un alcance acreditado.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        laboratorio_acreditado = st.checkbox(
            "Sí, el laboratorio está acreditado",
            key=f"laboratorio_acreditado_{codigo}",
            help=(
                "Al activarlo se habilitan Organismo acreditador "
                "y Alcance acreditado."
            ),
        )

        with st.form(
            f"form_calibracion_{codigo}",
            clear_on_submit=True,
        ):
            f1, f2 = st.columns(2)

            with f1:
                tipo_calibracion = st.selectbox(
                    "Tipo de calibración *",
                    TIPOS_CALIBRACION,
                )
                numero_certificado = st.text_input(
                    "Número de certificado",
                    placeholder="Ej.: CAL-2026-014",
                )
                laboratorio_calibracion = st.text_input(
                    "Laboratorio que realizó la calibración",
                )
                organismo_acreditador = st.text_input(
                    "Organismo acreditador",
                    placeholder="Ej.: ONAC",
                    disabled=not laboratorio_acreditado,
                )
                alcance_acreditado = st.text_input(
                    "Alcance acreditado",
                    placeholder=(
                        "Ej.: Masa, balanzas, intervalo y capacidad"
                    ),
                    disabled=not laboratorio_acreditado,
                )
                responsable_calibracion = st.text_input(
                    "Responsable",
                    value=str(
                        st.session_state.get(
                            "usuario",
                            responsable,
                        )
                    ),
                )

            with f2:
                fecha_calibracion = st.date_input(
                    "Fecha de calibración *",
                    value=None,
                )
                tiene_proxima = st.checkbox(
                    "Registrar próxima calibración",
                    value=True,
                )
                fecha_proxima_calibracion = (
                    st.date_input(
                        "Fecha de próxima calibración",
                        value=None,
                    )
                    if tiene_proxima
                    else None
                )
                frecuencia_meses = st.number_input(
                    "Frecuencia (meses)",
                    min_value=0,
                    max_value=120,
                    value=12,
                    step=1,
                )
                resultado_calibracion = st.selectbox(
                    "Resultado *",
                    ESTADOS_RESULTADO,
                )
                incertidumbre = st.text_input(
                    "Incertidumbre reportada",
                    placeholder="Ej.: ±0,002 g",
                )
                factor_cobertura = st.text_input(
                    "Factor de cobertura",
                    placeholder="Ej.: k = 2",
                )

            st.markdown("#### Trazabilidad metrológica")
            t1, t2, t3, t4 = st.columns(4)

            with t1:
                patron_utilizado = st.text_input(
                    "Patrón utilizado",
                )
            with t2:
                codigo_patron = st.text_input(
                    "Código del patrón",
                )
            with t3:
                certificado_patron = st.text_input(
                    "Certificado del patrón",
                )
            with t4:
                registrar_vencimiento_patron = st.checkbox(
                    "Patrón con vencimiento",
                )
                vencimiento_patron = (
                    st.date_input(
                        "Vencimiento del patrón",
                        value=None,
                    )
                    if registrar_vencimiento_patron
                    else None
                )

            documento_asociado = st.selectbox(
                "Certificado asociado en la Biblioteca Técnica",
                list(opciones_documento.keys()),
            )
            observaciones_calibracion = st.text_area(
                "Observaciones",
                placeholder=(
                    "Condiciones, restricciones, puntos fuera de "
                    "tolerancia o acciones derivadas."
                ),
            )
            guardar_calibracion = st.form_submit_button(
                "💾 Guardar calibración",
                type="primary",
                width="stretch",
            )

        if guardar_calibracion:
            if fecha_calibracion is None:
                st.error(
                    "Debe seleccionar la fecha de calibración."
                )
            elif (
                tiene_proxima
                and fecha_proxima_calibracion is None
            ):
                st.error(
                    "Debe seleccionar la fecha de próxima calibración."
                )
            elif (
                fecha_calibracion
                and fecha_proxima_calibracion
                and fecha_proxima_calibracion
                < fecha_calibracion
            ):
                st.error(
                    "La próxima calibración no puede ser anterior "
                    "a la fecha de calibración."
                )
            else:
                try:
                    registrar_calibracion(
                        codigo_equipo=codigo,
                        tipo_calibracion=tipo_calibracion,
                        numero_certificado=numero_certificado,
                        laboratorio_calibracion=(
                            laboratorio_calibracion
                        ),
                        laboratorio_acreditado=(
                            laboratorio_acreditado
                        ),
                        organismo_acreditador=(
                            organismo_acreditador
                        ),
                        alcance_acreditado=alcance_acreditado,
                        responsable=responsable_calibracion,
                        fecha_calibracion=fecha_calibracion,
                        fecha_proxima_calibracion=(
                            fecha_proxima_calibracion
                        ),
                        frecuencia_meses=frecuencia_meses,
                        resultado=resultado_calibracion,
                        incertidumbre=incertidumbre,
                        factor_cobertura=factor_cobertura,
                        patron_utilizado=patron_utilizado,
                        codigo_patron=codigo_patron,
                        certificado_patron=certificado_patron,
                        vencimiento_patron=vencimiento_patron,
                        documento_id=opciones_documento[
                            documento_asociado
                        ],
                        observaciones=observaciones_calibracion,
                        usuario_registro=str(
                            st.session_state.get(
                                "usuario",
                                responsable_calibracion,
                            )
                        ),
                    )
                    st.success(
                        "Calibración registrada correctamente."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "No fue posible guardar la calibración. "
                        f"Detalle: {exc}"
                    )

    st.markdown("### 📋 Historial de calibraciones")
    calibraciones = listar_calibraciones(codigo)

    if calibraciones.empty:
        st.info(
            "Este equipo todavía no tiene calibraciones registradas."
        )
    else:
        q1, q2 = st.columns(2)

        with q1:
            filtro_estado_cal = st.selectbox(
                "Filtrar por estado",
                [
                    "Todos",
                    "Vigente",
                    "Próxima a vencer",
                    "Vencida",
                    "Sin vencimiento",
                ],
                key=f"filtro_estado_cal_{codigo}",
            )

        with q2:
            filtro_resultado_cal = st.selectbox(
                "Filtrar por resultado",
                ["Todos"] + ESTADOS_RESULTADO,
                key=f"filtro_resultado_cal_{codigo}",
            )

        calibraciones_filtradas = calibraciones.copy()

        if filtro_estado_cal != "Todos":
            calibraciones_filtradas = calibraciones_filtradas[
                calibraciones_filtradas["estado"]
                == filtro_estado_cal
            ]

        if filtro_resultado_cal != "Todos":
            calibraciones_filtradas = calibraciones_filtradas[
                calibraciones_filtradas["resultado"]
                == filtro_resultado_cal
            ]

        st.caption(
            f"Mostrando {len(calibraciones_filtradas)} "
            f"de {len(calibraciones)} calibraciones."
        )

        for _, calibracion in calibraciones_filtradas.iterrows():
            estado_cal = str(
                calibracion.get("estado", "Sin estado")
            )

            icono_cal = {
                "Vigente": "🟢",
                "Próxima a vencer": "🟡",
                "Vencida": "🔴",
                "Sin vencimiento": "🔵",
            }.get(estado_cal, "⚪")

            certificado = (
                calibracion.get("numero_certificado")
                or "Sin número de certificado"
            )

            with st.container(border=True):
                h1, h2 = st.columns([4, 1])

                with h1:
                    st.markdown(
                        f"#### {icono_cal} {certificado}"
                    )
                    st.caption(
                        f"{calibracion.get('tipo_calibracion', '')} · "
                        f"{calibracion.get('laboratorio_calibracion') or 'Laboratorio no informado'}"
                    )

                with h2:
                    st.metric("Estado", estado_cal)

                r1, r2, r3, r4 = st.columns(4)
                r1.markdown(
                    "**Fecha calibración**  \n"
                    f"{calibracion.get('fecha_calibracion') or '—'}"
                )
                r2.markdown(
                    "**Próxima calibración**  \n"
                    f"{calibracion.get('fecha_proxima_calibracion') or 'No aplica'}"
                )
                r3.markdown(
                    "**Resultado**  \n"
                    f"{calibracion.get('resultado') or '—'}"
                )
                dias_cal = dias_para_vencimiento(
                    calibracion.get(
                        "fecha_proxima_calibracion"
                    )
                )
                r4.markdown(
                    "**Días restantes**  \n"
                    f"{dias_cal if dias_cal is not None else '—'}"
                )

                with st.expander("Ver detalle técnico"):
                    d1, d2 = st.columns(2)

                    with d1:
                        acreditado = (
                            "Sí"
                            if int(
                                calibracion.get(
                                    "laboratorio_acreditado",
                                    0,
                                )
                            )
                            else "No"
                        )
                        st.write(f"**Acreditado:** {acreditado}")
                        st.write(
                            "**Organismo acreditador:** "
                            f"{calibracion.get('organismo_acreditador') or '—'}"
                        )
                        st.write(
                            "**Alcance acreditado:** "
                            f"{calibracion.get('alcance_acreditado') or '—'}"
                        )
                        st.write(
                            "**Incertidumbre:** "
                            f"{calibracion.get('incertidumbre') or '—'}"
                        )
                        st.write(
                            "**Factor de cobertura:** "
                            f"{calibracion.get('factor_cobertura') or '—'}"
                        )

                    with d2:
                        st.write(
                            "**Patrón utilizado:** "
                            f"{calibracion.get('patron_utilizado') or '—'}"
                        )
                        st.write(
                            "**Código patrón:** "
                            f"{calibracion.get('codigo_patron') or '—'}"
                        )
                        st.write(
                            "**Certificado patrón:** "
                            f"{calibracion.get('certificado_patron') or '—'}"
                        )
                        st.write(
                            "**Vencimiento patrón:** "
                            f"{calibracion.get('vencimiento_patron') or '—'}"
                        )
                        st.write(
                            "**Responsable:** "
                            f"{calibracion.get('responsable') or '—'}"
                        )

                    observacion_cal = (
                        calibracion.get("observaciones") or ""
                    )
                    if observacion_cal:
                        st.markdown("**Observaciones**")
                        st.write(observacion_cal)

                b1, b2, b3 = st.columns([1.2, 1.2, 3])

                with b1:
                    ruta_documento = calibracion.get(
                        "documento_ruta"
                    )

                    if ruta_documento:
                        try:
                            contenido_certificado = leer_documento(
                                ruta_documento
                            )
                            st.download_button(
                                "⬇️ Certificado",
                                data=contenido_certificado,
                                file_name=calibracion.get(
                                    "documento_nombre"
                                )
                                or certificado,
                                mime=(
                                    calibracion.get("documento_mime")
                                    or "application/octet-stream"
                                ),
                                key=(
                                    "descargar_cal_"
                                    f"{calibracion.get('id')}"
                                ),
                                width="stretch",
                            )
                        except FileNotFoundError:
                            st.button(
                                "Certificado no disponible",
                                disabled=True,
                                key=(
                                    "cal_sin_archivo_"
                                    f"{calibracion.get('id')}"
                                ),
                                width="stretch",
                            )
                    else:
                        st.button(
                            "Sin certificado asociado",
                            disabled=True,
                            key=(
                                "cal_sin_doc_"
                                f"{calibracion.get('id')}"
                            ),
                            width="stretch",
                        )

                with b2:
                    confirmar_cal = st.checkbox(
                        "Confirmar eliminación",
                        key=(
                            "confirmar_cal_"
                            f"{calibracion.get('id')}"
                        ),
                    )

                    if st.button(
                        "🗑️ Eliminar",
                        key=(
                            "eliminar_cal_"
                            f"{calibracion.get('id')}"
                        ),
                        disabled=not confirmar_cal,
                        width="stretch",
                    ):
                        try:
                            eliminar_calibracion(
                                calibracion.get("id"),
                                usuario=str(
                                    st.session_state.get(
                                        "usuario",
                                        "",
                                    )
                                ),
                            )
                            st.success(
                                "Calibración eliminada."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                "No fue posible eliminar "
                                f"la calibración: {exc}"
                            )


with tabs[6]:
    st.markdown("### 🔧 Gestión de mantenimientos")
    st.caption(
        "Registro de intervenciones preventivas, correctivas, "
        "cambios de componentes, traslados y demás novedades técnicas."
    )

    resumen_mant = resumen_mantenimientos(codigo)

    mt1, mt2, mt3, mt4, mt5, mt6 = st.columns(6)
    mt1.metric("Total", resumen_mant["total"])
    mt2.metric("Preventivos", resumen_mant["preventivos"])
    mt3.metric("Correctivos", resumen_mant["correctivos"])
    mt4.metric(
        "Costo acumulado",
        f"$ {resumen_mant['costo_total']:,.0f}",
    )
    mt5.metric(
        "Horas fuera de servicio",
        f"{resumen_mant['horas_fuera_servicio']:.2f}",
    )
    mt6.metric(
        "Último mantenimiento",
        resumen_mant["ultimo_mantenimiento"] or "—",
    )

    mantenimientos = listar_mantenimientos(codigo)

    st.divider()

    with st.expander(
        "➕ Registrar mantenimiento o novedad técnica",
        expanded=mantenimientos.empty,
    ):
        documentos_mant = consultar_documentos_equipo(codigo)
        opciones_doc_mant = {"Sin documento asociado": None}

        if not documentos_mant.empty:
            for _, doc in documentos_mant.iterrows():
                etiqueta_doc = (
                    f"{doc.get('tipo_documento', 'Documento')} · "
                    f"{doc.get('nombre_archivo', '')}"
                )
                opciones_doc_mant[etiqueta_doc] = int(
                    doc.get("id")
                )

        with st.form(
            f"form_mantenimiento_{codigo}",
            clear_on_submit=True,
        ):
            ma1, ma2 = st.columns(2)

            with ma1:
                tipo_mantenimiento = st.selectbox(
                    "Tipo de mantenimiento *",
                    TIPOS_MANTENIMIENTO,
                )
                estado_mantenimiento = st.selectbox(
                    "Estado *",
                    ESTADOS_MANTENIMIENTO,
                    index=2,
                )
                fecha_inicio_mant = st.date_input(
                    "Fecha de inicio *",
                    value=None,
                )
                hora_inicio_mant = st.time_input(
                    "Hora de inicio",
                    value=None,
                )
                registrar_fin_mant = st.checkbox(
                    "Registrar finalización",
                    value=True,
                )
                fecha_fin_mant = (
                    st.date_input(
                        "Fecha de finalización",
                        value=None,
                    )
                    if registrar_fin_mant
                    else None
                )
                hora_fin_mant = (
                    st.time_input(
                        "Hora de finalización",
                        value=None,
                    )
                    if registrar_fin_mant
                    else None
                )

            with ma2:
                realizado_por_tipo = st.selectbox(
                    "Ejecutor",
                    TIPOS_EJECUTOR,
                )
                responsable_mant = st.text_input(
                    "Responsable",
                    value=str(
                        st.session_state.get(
                            "usuario",
                            responsable,
                        )
                    ),
                )
                proveedor_mant = st.text_input(
                    "Proveedor o empresa",
                    placeholder=(
                        "Obligatorio cuando el ejecutor sea "
                        "Proveedor externo"
                    ),
                    help=(
                        "Para personal interno puede dejarse vacío. "
                        "Para proveedor externo debe registrar la empresa."
                    ),
                )
                numero_orden_mant = st.text_input(
                    "Orden de trabajo o servicio",
                )
                resultado_mant = st.selectbox(
                    "Resultado",
                    RESULTADOS_MANTENIMIENTO,
                )

            st.markdown("#### Trabajo realizado")

            descripcion_mant = st.text_area(
                "Descripción del mantenimiento *",
                placeholder=(
                    "Ej.: Cambio de lámpara de deuterio, "
                    "cambio de electrodo, traslado de ubicación..."
                ),
            )

            tr1, tr2 = st.columns(2)

            with tr1:
                causa_mant = st.text_area(
                    "Causa o motivo",
                )

            with tr2:
                accion_realizada_mant = st.text_area(
                    "Acción realizada",
                )

            st.markdown("#### Componente o repuesto")

            cp1, cp2, cp3, cp4, cp5 = st.columns(5)

            with cp1:
                componente_mant = st.text_input(
                    "Componente",
                    placeholder="Ej.: Electrodo",
                )
            with cp2:
                marca_componente_mant = st.text_input(
                    "Marca",
                )
            with cp3:
                modelo_componente_mant = st.text_input(
                    "Modelo / referencia",
                )
            with cp4:
                serie_componente_mant = st.text_input(
                    "Serie / lote",
                )
            with cp5:
                cantidad_mant = st.number_input(
                    "Cantidad",
                    min_value=1,
                    max_value=999,
                    value=1,
                    step=1,
                )

            st.markdown("#### Costos")

            co1, co2, co3 = st.columns(3)

            with co1:
                costo_repuesto_mant = st.number_input(
                    "Costo de repuestos",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                )
            with co2:
                costo_mano_obra_mant = st.number_input(
                    "Costo de mano de obra",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                )
            with co3:
                costo_otros_mant = st.number_input(
                    "Otros costos",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                )

            documento_mant = st.selectbox(
                "Documento asociado en la Biblioteca Técnica",
                list(opciones_doc_mant.keys()),
            )

            observaciones_mant = st.text_area(
                "Observaciones",
            )

            guardar_mant = st.form_submit_button(
                "💾 Guardar mantenimiento",
                type="primary",
                width="stretch",
            )

        if guardar_mant:
            if fecha_inicio_mant is None:
                st.error(
                    "Debe seleccionar la fecha de inicio."
                )
            elif not descripcion_mant.strip():
                st.error(
                    "Debe describir el mantenimiento."
                )
            elif (
                registrar_fin_mant
                and fecha_fin_mant is None
            ):
                st.error(
                    "Debe seleccionar la fecha de finalización."
                )
            elif (
                realizado_por_tipo == "Proveedor externo"
                and not proveedor_mant.strip()
            ):
                st.error(
                    "Debe registrar el proveedor o empresa que "
                    "realizó el mantenimiento."
                )
            else:
                try:
                    registrar_mantenimiento(
                        codigo_equipo=codigo,
                        tipo_mantenimiento=tipo_mantenimiento,
                        estado_mantenimiento=(
                            estado_mantenimiento
                        ),
                        fecha_inicio=fecha_inicio_mant,
                        hora_inicio=hora_inicio_mant,
                        fecha_fin=fecha_fin_mant,
                        hora_fin=hora_fin_mant,
                        realizado_por_tipo=realizado_por_tipo,
                        responsable=responsable_mant,
                        proveedor=proveedor_mant,
                        numero_orden=numero_orden_mant,
                        descripcion=descripcion_mant,
                        causa=causa_mant,
                        accion_realizada=(
                            accion_realizada_mant
                        ),
                        resultado=resultado_mant,
                        componente=componente_mant,
                        marca_componente=(
                            marca_componente_mant
                        ),
                        modelo_componente=(
                            modelo_componente_mant
                        ),
                        serie_componente=(
                            serie_componente_mant
                        ),
                        cantidad=cantidad_mant,
                        costo_repuesto=costo_repuesto_mant,
                        costo_mano_obra=(
                            costo_mano_obra_mant
                        ),
                        costo_otros=costo_otros_mant,
                        documento_id=opciones_doc_mant[
                            documento_mant
                        ],
                        observaciones=observaciones_mant,
                        usuario_registro=str(
                            st.session_state.get(
                                "usuario",
                                responsable_mant,
                            )
                        ),
                    )

                    st.success(
                        "Mantenimiento registrado correctamente."
                    )
                    st.rerun()

                except Exception as exc:
                    st.error(
                        "No fue posible guardar el mantenimiento. "
                        f"Detalle: {exc}"
                    )

    st.markdown("### 📋 Historial de mantenimientos")

    mantenimientos = listar_mantenimientos(codigo)

    if mantenimientos.empty:
        st.info(
            "Este equipo todavía no tiene mantenimientos "
            "o novedades técnicas registradas."
        )

    else:
        mf1, mf2 = st.columns(2)

        with mf1:
            filtro_tipo_mant = st.selectbox(
                "Filtrar por tipo",
                ["Todos"] + TIPOS_MANTENIMIENTO,
                key=f"filtro_tipo_mant_{codigo}",
            )

        with mf2:
            filtro_estado_mant = st.selectbox(
                "Filtrar por estado",
                ["Todos"] + ESTADOS_MANTENIMIENTO,
                key=f"filtro_estado_mant_{codigo}",
            )

        mantenimientos_filtrados = mantenimientos.copy()

        if filtro_tipo_mant != "Todos":
            mantenimientos_filtrados = (
                mantenimientos_filtrados[
                    mantenimientos_filtrados[
                        "tipo_mantenimiento"
                    ]
                    == filtro_tipo_mant
                ]
            )

        if filtro_estado_mant != "Todos":
            mantenimientos_filtrados = (
                mantenimientos_filtrados[
                    mantenimientos_filtrados[
                        "estado_mantenimiento"
                    ]
                    == filtro_estado_mant
                ]
            )

        st.caption(
            f"Mostrando {len(mantenimientos_filtrados)} "
            f"de {len(mantenimientos)} registros."
        )

        for _, mant in mantenimientos_filtrados.iterrows():
            tipo_mant = str(
                mant.get("tipo_mantenimiento", "Mantenimiento")
            )
            estado_mant = str(
                mant.get("estado_mantenimiento", "Sin estado")
            )

            icono_mant = {
                "Preventivo": "🟢",
                "Correctivo": "🔴",
                "Ajuste": "🟡",
                "Cambio de componente": "🔄",
                "Traslado": "🚚",
                "Baja temporal": "🛑",
                "Baja definitiva": "⚫",
            }.get(tipo_mant, "🔧")

            with st.container(border=True):
                mh1, mh2 = st.columns([4, 1])

                with mh1:
                    st.markdown(
                        f"#### {icono_mant} {tipo_mant}"
                    )
                    st.caption(
                        f"{mant.get('fecha_inicio') or 'Sin fecha'} · "
                        f"{mant.get('descripcion') or ''}"
                    )

                with mh2:
                    st.metric(
                        "Estado",
                        estado_mant,
                    )

                md1, md2, md3, md4 = st.columns(4)

                md1.markdown(
                    "**Resultado**  \n"
                    f"{mant.get('resultado') or '—'}"
                )
                md2.markdown(
                    "**Responsable**  \n"
                    f"{mant.get('responsable') or '—'}"
                )
                md3.markdown(
                    "**Costo total**  \n"
                    f"$ {float(mant.get('costo_total') or 0):,.0f}"
                )
                md4.markdown(
                    "**Horas fuera de servicio**  \n"
                    f"{float(mant.get('horas_fuera_servicio') or 0):.2f}"
                )

                with st.expander("Ver detalle técnico"):
                    de1, de2 = st.columns(2)

                    with de1:
                        st.write(
                            "**Causa:** "
                            f"{mant.get('causa') or '—'}"
                        )
                        st.write(
                            "**Acción realizada:** "
                            f"{mant.get('accion_realizada') or '—'}"
                        )
                        st.write(
                            "**Ejecutor:** "
                            f"{mant.get('realizado_por_tipo') or '—'}"
                        )
                        st.write(
                            "**Proveedor:** "
                            f"{mant.get('proveedor') or '—'}"
                        )
                        st.write(
                            "**Orden:** "
                            f"{mant.get('numero_orden') or '—'}"
                        )

                    with de2:
                        st.write(
                            "**Componente:** "
                            f"{mant.get('componente') or '—'}"
                        )
                        st.write(
                            "**Marca:** "
                            f"{mant.get('marca_componente') or '—'}"
                        )
                        st.write(
                            "**Modelo / referencia:** "
                            f"{mant.get('modelo_componente') or '—'}"
                        )
                        st.write(
                            "**Serie / lote:** "
                            f"{mant.get('serie_componente') or '—'}"
                        )
                        st.write(
                            "**Cantidad:** "
                            f"{mant.get('cantidad') or 1}"
                        )

                    if mant.get("observaciones"):
                        st.markdown("**Observaciones**")
                        st.write(mant.get("observaciones"))

                mb1, mb2, mb3 = st.columns([1.2, 1.2, 3])

                with mb1:
                    ruta_doc_mant = mant.get("documento_ruta")

                    if ruta_doc_mant:
                        try:
                            contenido_doc_mant = leer_documento(
                                ruta_doc_mant
                            )

                            st.download_button(
                                "⬇️ Documento",
                                data=contenido_doc_mant,
                                file_name=(
                                    mant.get("documento_nombre")
                                    or "documento_mantenimiento"
                                ),
                                mime=(
                                    mant.get("documento_mime")
                                    or "application/octet-stream"
                                ),
                                key=(
                                    "descargar_mant_"
                                    f"{mant.get('id')}"
                                ),
                                width="stretch",
                            )

                        except FileNotFoundError:
                            st.button(
                                "Documento no disponible",
                                disabled=True,
                                key=(
                                    "mant_sin_archivo_"
                                    f"{mant.get('id')}"
                                ),
                                width="stretch",
                            )
                    else:
                        st.button(
                            "Sin documento asociado",
                            disabled=True,
                            key=(
                                "mant_sin_doc_"
                                f"{mant.get('id')}"
                            ),
                            width="stretch",
                        )

                with mb2:
                    confirmar_mant = st.checkbox(
                        "Confirmar eliminación",
                        key=(
                            "confirmar_mant_"
                            f"{mant.get('id')}"
                        ),
                    )

                    if st.button(
                        "🗑️ Eliminar",
                        key=(
                            "eliminar_mant_"
                            f"{mant.get('id')}"
                        ),
                        disabled=not confirmar_mant,
                        width="stretch",
                    ):
                        try:
                            eliminar_mantenimiento(
                                mant.get("id"),
                                usuario=str(
                                    st.session_state.get(
                                        "usuario",
                                        "",
                                    )
                                ),
                            )
                            st.success(
                                "Mantenimiento eliminado."
                            )
                            st.rerun()

                        except Exception as exc:
                            st.error(
                                "No fue posible eliminar "
                                f"el mantenimiento: {exc}"
                            )


with tabs[7]:
    st.markdown("### 📂 Biblioteca técnica del equipo")
    st.caption(
        "Gestión centralizada de certificados, manuales, procedimientos, "
        "informes, fotografías y demás soportes asociados al equipo."
    )

    documentos = consultar_documentos_equipo(codigo)

    total_documentos = len(documentos)
    vigentes = (
        int((documentos["estado"] == "Vigente").sum())
        if not documentos.empty and "estado" in documentos.columns
        else 0
    )
    proximos = (
        int((documentos["estado"] == "Próximo a vencer").sum())
        if not documentos.empty and "estado" in documentos.columns
        else 0
    )
    vencidos = (
        int((documentos["estado"] == "Vencido").sum())
        if not documentos.empty and "estado" in documentos.columns
        else 0
    )
    sin_vencimiento = (
        int((documentos["estado"] == "Sin vencimiento").sum())
        if not documentos.empty and "estado" in documentos.columns
        else 0
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", total_documentos)
    m2.metric("🟢 Vigentes", vigentes)
    m3.metric("🟡 Próximos", proximos)
    m4.metric("🔴 Vencidos", vencidos)
    m5.metric("🔵 Sin vencimiento", sin_vencimiento)

    st.divider()

    with st.expander(
        "➕ Registrar nuevo documento",
        expanded=documentos.empty,
    ):
        with st.form(
            f"form_documento_{codigo}",
            clear_on_submit=True,
        ):
            c1, c2 = st.columns(2)

            with c1:
                tipo_documento = st.selectbox(
                    "Tipo de documento *",
                    [
                        "Certificado de calibración",
                        "Certificado de verificación",
                        "Certificado de mantenimiento",
                        "Manual del fabricante",
                        "Procedimiento",
                        "Instructivo",
                        "Ficha técnica",
                        "Hoja de seguridad",
                        "Informe técnico",
                        "Fotografía",
                        "Registro de auditoría",
                        "Calificación",
                        "Otro",
                    ],
                )

                titulo_documento = st.text_input(
                    "Título",
                    placeholder="Ej.: Certificado de calibración 2026",
                )

                archivo_documento = st.file_uploader(
                    "Seleccionar archivo *",
                    type=[
                        "pdf",
                        "png",
                        "jpg",
                        "jpeg",
                        "webp",
                        "doc",
                        "docx",
                        "xls",
                        "xlsx",
                        "csv",
                        "txt",
                        "zip",
                    ],
                    help="Tamaño recomendado máximo: 20 MB.",
                )

                responsable_documento = st.text_input(
                    "Responsable",
                    value=str(st.session_state.get("usuario", "")),
                )

                proveedor_documento = st.text_input(
                    "Proveedor o emisor",
                )

            with c2:
                registrar_emision = st.checkbox(
                    "Registrar fecha de emisión",
                    value=True,
                )

                fecha_emision_documento = (
                    st.date_input(
                        "Fecha de emisión",
                        value=None,
                    )
                    if registrar_emision
                    else None
                )

                tiene_vencimiento = st.checkbox(
                    "Tiene fecha de vencimiento",
                )

                fecha_vencimiento_documento = (
                    st.date_input(
                        "Fecha de vencimiento",
                        value=None,
                    )
                    if tiene_vencimiento
                    else None
                )

                version_documento = st.text_input(
                    "Versión",
                    placeholder="Ej.: 01",
                )

                observaciones_documento = st.text_area(
                    "Observaciones",
                    placeholder=(
                        "Alcance, restricciones, número de certificado "
                        "o información complementaria."
                    ),
                )

            guardar_documento = st.form_submit_button(
                "💾 Guardar documento",
                type="primary",
                width="stretch",
            )

        if guardar_documento:
            if archivo_documento is None:
                st.error("Debe seleccionar un archivo.")

            elif (
                tiene_vencimiento
                and fecha_emision_documento
                and fecha_vencimiento_documento
                and fecha_vencimiento_documento
                < fecha_emision_documento
            ):
                st.error(
                    "La fecha de vencimiento no puede ser anterior "
                    "a la fecha de emisión."
                )

            elif tiene_vencimiento and fecha_vencimiento_documento is None:
                st.error(
                    "Debe seleccionar la fecha de vencimiento."
                )

            else:
                try:
                    registrar_documento(
                        codigo,
                        tipo_documento,
                        archivo_documento,
                        titulo_documento,
                        fecha_emision_documento,
                        fecha_vencimiento_documento,
                        responsable_documento,
                        proveedor_documento,
                        version_documento,
                        observaciones_documento,
                    )

                    st.success(
                        "Documento registrado correctamente."
                    )
                    st.rerun()

                except Exception as exc:
                    st.error(
                        "No fue posible guardar el documento. "
                        f"Detalle: {exc}"
                    )

    st.markdown("### 🔎 Consulta documental")

    documentos = consultar_documentos_equipo(codigo)

    if documentos.empty:
        st.info(
            "Este equipo todavía no tiene documentos registrados."
        )

    else:
        f1, f2, f3 = st.columns(3)

        tipos_disponibles = sorted(
            documentos["tipo_documento"]
            .fillna("")
            .astype(str)
            .unique()
            .tolist()
        )

        estados_disponibles = sorted(
            documentos["estado"]
            .fillna("")
            .astype(str)
            .unique()
            .tolist()
        )

        with f1:
            filtro_tipo = st.selectbox(
                "Tipo",
                ["Todos"] + tipos_disponibles,
                key=f"filtro_tipo_doc_{codigo}",
            )

        with f2:
            filtro_estado = st.selectbox(
                "Estado",
                ["Todos"] + estados_disponibles,
                key=f"filtro_estado_doc_{codigo}",
            )

        with f3:
            texto_busqueda = st.text_input(
                "Buscar",
                placeholder="Título, archivo, proveedor...",
                key=f"buscar_doc_{codigo}",
            )

        documentos_filtrados = documentos.copy()

        if filtro_tipo != "Todos":
            documentos_filtrados = documentos_filtrados[
                documentos_filtrados["tipo_documento"]
                == filtro_tipo
            ]

        if filtro_estado != "Todos":
            documentos_filtrados = documentos_filtrados[
                documentos_filtrados["estado"]
                == filtro_estado
            ]

        if texto_busqueda.strip():
            patron = texto_busqueda.strip().lower()
            mascara = pd.Series(
                False,
                index=documentos_filtrados.index,
            )

            for columna in [
                "titulo",
                "nombre_archivo",
                "proveedor",
                "responsable",
                "version",
                "observaciones",
            ]:
                if columna in documentos_filtrados.columns:
                    mascara = mascara | (
                        documentos_filtrados[columna]
                        .fillna("")
                        .astype(str)
                        .str.lower()
                        .str.contains(
                            patron,
                            regex=False,
                        )
                    )

            documentos_filtrados = documentos_filtrados[
                mascara
            ]

        st.caption(
            f"Mostrando {len(documentos_filtrados)} "
            f"de {len(documentos)} documentos."
        )

        if documentos_filtrados.empty:
            st.warning(
                "No hay documentos que coincidan con los filtros."
            )

        else:
            for _, documento in documentos_filtrados.iterrows():
                estado_doc = str(
                    documento.get("estado", "Sin estado")
                )

                icono = {
                    "Vigente": "🟢",
                    "Próximo a vencer": "🟡",
                    "Vencido": "🔴",
                    "Sin vencimiento": "🔵",
                    "Fecha inválida": "⚫",
                }.get(estado_doc, "⚪")

                titulo_doc = (
                    documento.get("titulo")
                    or documento.get("nombre_archivo")
                    or "Documento sin título"
                )

                with st.container(border=True):
                    i1, i2 = st.columns([4, 1])

                    with i1:
                        st.markdown(
                            f"#### {icono} {titulo_doc}"
                        )
                        st.caption(
                            str(
                                documento.get(
                                    "nombre_archivo",
                                    "",
                                )
                            )
                        )

                    with i2:
                        st.metric(
                            "Estado",
                            estado_doc,
                        )

                    d1, d2, d3, d4 = st.columns(4)

                    d1.markdown(
                        "**Tipo**  \n"
                        f"{documento.get('tipo_documento') or '—'}"
                    )
                    d2.markdown(
                        "**Emisión**  \n"
                        f"{documento.get('fecha_emision') or '—'}"
                    )
                    d3.markdown(
                        "**Vencimiento**  \n"
                        f"{documento.get('fecha_vencimiento') or 'No aplica'}"
                    )
                    d4.markdown(
                        "**Versión**  \n"
                        f"{documento.get('version') or '—'}"
                    )

                    proveedor_doc = (
                        documento.get("proveedor")
                        or "No informado"
                    )
                    responsable_doc = (
                        documento.get("responsable")
                        or "No informado"
                    )

                    st.caption(
                        f"Proveedor o emisor: {proveedor_doc} · "
                        f"Responsable: {responsable_doc}"
                    )

                    observaciones_doc = str(
                        documento.get("observaciones") or ""
                    ).strip()

                    if observaciones_doc:
                        with st.expander(
                            "Ver observaciones",
                        ):
                            st.write(observaciones_doc)

                    a1, a2, a3 = st.columns([1.2, 1.2, 3])

                    with a1:
                        try:
                            contenido_documento = leer_documento(
                                documento.get("ruta_archivo")
                            )

                            st.download_button(
                                "⬇️ Descargar",
                                data=contenido_documento,
                                file_name=documento.get(
                                    "nombre_archivo"
                                ),
                                mime=(
                                    documento.get("mime_type")
                                    or "application/octet-stream"
                                ),
                                key=(
                                    "descargar_doc_"
                                    f"{documento.get('id')}"
                                ),
                                width="stretch",
                            )

                        except FileNotFoundError:
                            st.button(
                                "Archivo no disponible",
                                disabled=True,
                                key=(
                                    "archivo_no_disponible_"
                                    f"{documento.get('id')}"
                                ),
                                width="stretch",
                            )

                    with a2:
                        confirmar_eliminacion = st.checkbox(
                            "Confirmar eliminación",
                            key=(
                                "confirmar_doc_"
                                f"{documento.get('id')}"
                            ),
                        )

                        if st.button(
                            "🗑️ Eliminar",
                            key=(
                                "eliminar_doc_"
                                f"{documento.get('id')}"
                            ),
                            disabled=not confirmar_eliminacion,
                            width="stretch",
                        ):
                            try:
                                eliminar_documento(
                                    documento.get("id"),
                                    usuario=str(
                                        st.session_state.get(
                                            "usuario",
                                            "",
                                        )
                                    ),
                                )

                                st.success(
                                    "Documento eliminado."
                                )
                                st.rerun()

                            except Exception as exc:
                                st.error(
                                    "No fue posible eliminar "
                                    f"el documento: {exc}"
                                )

                    with a3:
                        try:
                            leer_documento(
                                documento.get("ruta_archivo")
                            )
                        except FileNotFoundError:
                            st.warning(
                                "El registro existe en SQLite, pero "
                                "el archivo físico no está disponible "
                                "en este despliegue."
                            )

with tabs[8]:
    st.markdown("### Auditoría")
    st.info("Aquí se mostrará el historial de cambios y trazabilidad del equipo.")