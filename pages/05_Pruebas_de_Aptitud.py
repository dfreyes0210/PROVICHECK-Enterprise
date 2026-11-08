"""PROVICHECK | Pruebas de Aptitud. Catálogos configurables desde Excel."""

import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.pruebas_aptitud_catalogos import (
    listar_materiales_catalogo,
    listar_ensayos_catalogo,
    preparar_parametros_campana,
)
from utils.pruebas_aptitud_estadistica import (
    evaluar_parametro,
    evaluar_simulacion_color,
)
from utils.pruebas_aptitud_db import (
    listar_campanas,
    listar_materiales,
    listar_parametros,
    crear_campana_borrador,
    publicar_campana,
    consultar_mi_participacion,
    registrar_mi_participacion,
    listar_parametros_registro,
    consultar_mi_borrador,
    guardar_mi_borrador,
    enviar_mis_resultados_definitivos,
)
from utils.ui import (
    aplicar_estilo,
    encabezado,
    pie_pagina,
    requerir_autenticacion,
    sidebar_pro,
)

ZONA = ZoneInfo("America/Bogota")


def norm(valor):
    texto = " ".join(str(valor or "").casefold().split())
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def fecha(dia, hora):
    return datetime.combine(dia, hora, tzinfo=ZONA)


def convertir_fecha(valor):
    if isinstance(valor, datetime):
        return valor.astimezone(ZONA)
    return datetime.fromisoformat(
        str(valor).replace("Z", "+00:00")
    ).astimezone(ZONA)


def mostrar_fecha(valor):
    if not valor:
        return "Plazo general"
    return convertir_fecha(valor).strftime("%d/%m/%Y %H:%M")


def formato_numero(valor, decimales=2):
    if valor is None:
        return "—"
    return f"{valor:,.{decimales}f}"


st.set_page_config(
    page_title="Pruebas de Aptitud | PROVICHECK",
    page_icon="🧪",
    layout="wide",
)

aplicar_estilo()
requerir_autenticacion()

usuario = str(st.session_state.get("id_usuario") or "").strip()
rol = norm(st.session_state.get("rol"))
laboratorio = norm(st.session_state.get("laboratorio_asignado"))

laboratorio_valido = laboratorio in {
    "fabrica",
    "laboratorio de fabrica",
    "laboratorio fabrica",
}

autorizado = (
    st.session_state.get("autenticado") is True
    and bool(usuario)
    and (
        rol == "administrador"
        or (
            laboratorio_valido
            and rol in {"lider", "analista"}
        )
    )
)

if not autorizado:
    st.error("Acceso restringido al Laboratorio de Fábrica.")
    st.stop()

gestor = rol == "administrador" or (
    rol == "lider" and laboratorio_valido
)

sidebar_pro()
encabezado()

st.markdown("## 🧪 Pruebas de Aptitud")
st.caption("Evaluación interanalistas · Laboratorio de Fábrica")

col1, col2, col3 = st.columns(3)
col1.metric("Participante", usuario)
col2.metric("Laboratorio", "Fábrica")
col3.metric("Fecha", datetime.now(ZONA).strftime("%d/%m/%Y"))

st.info(
    "Módulo de comparación interanalistas. Las evaluaciones "
    "definitivas requieren criterios estadísticos aprobados "
    "y pruebas integrales previas a producción."
)

tab_campanas, tab_resultados, tab_evaluacion, tab_informes = st.tabs(
    [
        "📅 Campañas",
        "🧪 Registrar resultados",
        "📊 Evaluación y dashboard",
        "📄 Informes",
    ]
)

# ============================================================
# 1. CAMPAÑAS
# ============================================================

with tab_campanas:
    st.subheader("Campañas registradas")

    try:
        campanas = listar_campanas()

        if not campanas:
            st.info("Todavía no hay campañas registradas.")

        for campana in campanas:
            etiqueta = (
                f"{campana['codigo']} · "
                f"{campana['titulo']} · "
                f"{campana['estado']}"
            )

            with st.expander(etiqueta):
                st.write(
                    f"Apertura: {mostrar_fecha(campana['fecha_apertura'])} "
                    f"| Cierre: {mostrar_fecha(campana['fecha_cierre'])}"
                )

                for material in listar_materiales(campana["id"]):
                    st.markdown(f"**{material['nombre']}**")

                    if material.get("fecha_apertura"):
                        st.caption(
                            "Plazo particular: "
                            f"{mostrar_fecha(material['fecha_apertura'])} "
                            "a "
                            f"{mostrar_fecha(material['fecha_cierre'])}"
                        )

                    parametros = listar_parametros(material["id"])
                    st.caption(
                        "Parámetros: "
                        + ", ".join(p["nombre"] for p in parametros)
                    )

                if gestor and campana["estado"] == "borrador":
                    st.divider()
                    st.warning(
                        "Publicar permite que los analistas vean esta "
                        "campaña. Esta acción no se revierte desde "
                        "esta pantalla."
                    )

                    confirmar = st.checkbox(
                        "Confirmo que revisé materiales, parámetros y fechas",
                        key=f"pa_confirma_{campana['id']}",
                    )

                    if st.button(
                        "📢 Publicar campaña",
                        key=f"pa_publicar_{campana['id']}",
                        disabled=not confirmar,
                        type="primary",
                    ):
                        try:
                            publicar_campana(campana["id"])
                            st.success(
                                "Campaña publicada correctamente "
                                "y registrada en auditoría."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"No se pudo publicar: {exc}")

    except Exception as exc:
        st.error(f"Error consultando campañas: {exc}")

    # --------------------------------------------------------
    # CREACIÓN DE CAMPAÑAS DESDE CATÁLOGOS EXCEL
    # --------------------------------------------------------

    if gestor:
        st.divider()
        st.subheader("Crear campaña en borrador")

        if "pa_nmateriales" not in st.session_state:
            st.session_state.pa_nmateriales = 1

        try:
            catalogo_materiales = listar_materiales_catalogo()
        except Exception as exc:
            catalogo_materiales = []
            st.error(
                "No fue posible leer PA_Materiales "
                f"del Excel maestro: {exc}"
            )

        if not catalogo_materiales:
            st.warning(
                "No se puede crear una campaña sin materiales "
                "activos en el catálogo."
            )
        else:
            st.caption(
                "Los materiales y ensayos se leen del Excel maestro. "
                "Se muestran únicamente los ensayos habilitados "
                "para Providencia. El azúcar refinado permanece "
                "disponible en el catálogo."
            )

            opciones_materiales = {
                material["id"]: material["nombre"]
                for material in catalogo_materiales
            }

            with st.container():
                c1, c2 = st.columns([1, 2])

                codigo = c1.text_input(
                    "Código de campaña *",
                    placeholder="PA-2026-001",
                )

                titulo = c2.text_input("Título *")

                descripcion = st.text_area(
                    "Descripción",
                    height=70,
                )

                d1, h1, d2, h2 = st.columns(4)
                hoy = datetime.now(ZONA).date()

                apertura_d = d1.date_input(
                    "Apertura general",
                    value=hoy,
                )
                apertura_h = h1.time_input(
                    "Hora apertura",
                    value=time(8, 0),
                )
                cierre_d = d2.date_input(
                    "Cierre general",
                    value=hoy + timedelta(days=7),
                )
                cierre_h = h2.time_input(
                    "Hora cierre",
                    value=time(17, 0),
                )

                materiales_campana = []

                for indice in range(st.session_state.pa_nmateriales):
                    with st.container(border=True):
                        st.markdown(
                            f"**Material {indice + 1}**"
                        )

                        m1, m2 = st.columns(2)

                        id_material = m1.selectbox(
                            "Material *",
                            options=list(opciones_materiales),
                            format_func=lambda identificador: (
                                opciones_materiales[identificador]
                            ),
                            key=f"pa_catalogo_material_{indice}",
                        )

                        nombre_material = opciones_materiales[id_material]

                        codigo_muestra = m2.text_input(
                            "Código de muestra",
                            key=f"pa_muestra_{indice}",
                        )

                        descripcion_material = st.text_input(
                            "Descripción del material",
                            key=f"pa_descripcion_{indice}",
                        )

                        particular = st.checkbox(
                            "Fechas particulares para este material",
                            key=f"pa_particular_{indice}",
                        )

                        inicio_material = None
                        fin_material = None

                        if particular:
                            x1, x2, x3, x4 = st.columns(4)

                            inicio_material = fecha(
                                x1.date_input(
                                    "Apertura",
                                    value=apertura_d,
                                    key=f"pa_mi_d_{indice}",
                                ),
                                x2.time_input(
                                    "Hora",
                                    value=apertura_h,
                                    key=f"pa_mi_h_{indice}",
                                ),
                            )

                            fin_material = fecha(
                                x3.date_input(
                                    "Cierre",
                                    value=cierre_d,
                                    key=f"pa_mf_d_{indice}",
                                ),
                                x4.time_input(
                                    "Hora",
                                    value=cierre_h,
                                    key=f"pa_mf_h_{indice}",
                                ),
                            )

                        try:
                            ensayos = listar_ensayos_catalogo(
                                id_material,
                                solo_providencia=True,
                            )
                        except Exception as exc:
                            ensayos = []
                            st.error(
                                f"Error leyendo los ensayos de "
                                f"{nombre_material}: {exc}"
                            )

                        opciones_ensayos = {
                            ensayo["id"]: ensayo
                            for ensayo in ensayos
                        }

                        seleccion = st.multiselect(
                            "Ensayos para este material *",
                            options=list(opciones_ensayos),
                            format_func=lambda identificador: (
                                f"{opciones_ensayos[identificador]['etiqueta']} "
                                f"({opciones_ensayos[identificador]['unidad']})"
                            ),
                            key=(
                                f"pa_catalogo_ensayos_"
                                f"{indice}_{id_material}"
                            ),
                        )

                        if not ensayos:
                            st.warning(
                                "No hay ensayos habilitados para este "
                                "material en Providencia."
                            )

                        parametros = (
                            preparar_parametros_campana(
                                [
                                    opciones_ensayos[identificador]
                                    for identificador in seleccion
                                ]
                            )
                            if seleccion
                            else []
                        )

                        materiales_campana.append(
                            {
                                "nombre": nombre_material,
                                "codigo_muestra": codigo_muestra,
                                "descripcion": descripcion_material,
                                "fecha_apertura": inicio_material,
                                "fecha_cierre": fin_material,
                                "parametros": parametros,
                            }
                        )

                guardar_campana = st.button(
                    "💾 Guardar campaña en borrador",
                    type="primary",
                )

            b1, b2 = st.columns(2)

            if b1.button(
                "➕ Agregar material",
                use_container_width=True,
            ):
                st.session_state.pa_nmateriales += 1
                st.rerun()

            if b2.button(
                "➖ Quitar último material",
                disabled=st.session_state.pa_nmateriales <= 1,
                use_container_width=True,
            ):
                st.session_state.pa_nmateriales -= 1
                st.rerun()

            if guardar_campana:
                try:
                    datos = {
                        "codigo": codigo,
                        "titulo": titulo,
                        "descripcion": descripcion,
                        "fecha_apertura": fecha(
                            apertura_d, apertura_h
                        ),
                        "fecha_cierre": fecha(
                            cierre_d, cierre_h
                        ),
                        "materiales": materiales_campana,
                    }

                    nuevo_id = crear_campana_borrador(datos)

                    st.success(
                        f"Campaña creada correctamente. "
                        f"ID {nuevo_id}; estado borrador."
                    )
                    st.caption(
                        "Actualiza la página para verla en el listado."
                    )

                except Exception as exc:
                    st.error(f"No se pudo guardar: {exc}")


# ============================================================
# 2. REGISTRO DE RESULTADOS
# ============================================================

with tab_resultados:
    st.subheader("Participación en campañas publicadas")

    st.caption(
        "La declaración se registra una sola vez por campaña "
        "y no puede editarse desde esta pantalla."
    )

    st.info(
        "Puedes guardar borradores y enviar definitivamente "
        "los resultados por material. Después del envío "
        "no podrás modificarlos."
    )

    try:
        publicadas = [
            campana
            for campana in listar_campanas()
            if campana["estado"] == "publicada"
        ]

        if not publicadas:
            st.info("No hay campañas publicadas disponibles.")

        for campana in publicadas:
            with st.container(border=True):
                st.markdown(
                    f"**{campana['codigo']} · {campana['titulo']}**"
                )

                st.caption(
                    f"Apertura: {mostrar_fecha(campana['fecha_apertura'])} "
                    f"| Cierre: {mostrar_fecha(campana['fecha_cierre'])}"
                )

                participacion = consultar_mi_participacion(
                    campana["id"]
                )

                if participacion:
                    st.success(
                        "Tu aceptación y declaración ya quedaron registradas."
                    )

                    if participacion.get("conflicto_interes"):
                        st.warning(
                            "Declaraste un conflicto de interés. "
                            "Tu participación queda bloqueada para "
                            "el registro de resultados hasta que "
                            "exista una revisión formal."
                        )
                    else:
                        st.caption(
                            "Sin conflicto de interés declarado. "
                            "Puedes registrar borradores durante "
                            "las fechas habilitadas."
                        )
                else:
                    ahora = datetime.now(ZONA)
                    apertura = convertir_fecha(
                        campana["fecha_apertura"]
                    )
                    cierre = convertir_fecha(
                        campana["fecha_cierre"]
                    )

                    if not apertura <= ahora <= cierre:
                        st.warning(
                            "La campaña no está dentro del periodo "
                            "habilitado para participar."
                        )
                    else:
                        with st.form(
                            f"pa_participacion_{campana['id']}"
                        ):
                            st.markdown(
                                "**Condiciones de participación**"
                            )

                            st.write(
                                "Me comprometo a analizar las muestras "
                                "de manera independiente, mantener "
                                "la confidencialidad de los resultados, "
                                "seguir los métodos vigentes y reportar "
                                "cualquier situación que comprometa "
                                "mi imparcialidad."
                            )

                            acepto = st.checkbox(
                                "He leído y acepto las condiciones "
                                "de participación."
                            )

                            conflicto = st.radio(
                                "¿Existe algún conflicto de interés "
                                "o impedimento?",
                                [
                                    "Selecciona una respuesta",
                                    "No",
                                    "Sí",
                                ],
                                horizontal=True,
                            )

                            detalle = st.text_area(
                                "Describe el conflicto o impedimento "
                                "(obligatorio si respondes Sí)",
                                max_chars=2000,
                            )

                            enviar = st.form_submit_button(
                                "Registrar aceptación y declaración",
                                type="primary",
                            )

                        if enviar:
                            try:
                                if conflicto == "Selecciona una respuesta":
                                    raise ValueError(
                                        "Selecciona Sí o No en la "
                                        "declaración de conflicto de interés."
                                    )

                                registrar_mi_participacion(
                                    campana["id"],
                                    acepto,
                                    conflicto == "Sí",
                                    detalle,
                                )

                                st.success(
                                    "Participación registrada correctamente."
                                )
                                st.rerun()

                            except Exception as exc:
                                st.error(
                                    "No fue posible registrar tu "
                                    f"participación: {exc}"
                                )

    except Exception as exc:
        st.error(
            f"No fue posible consultar las participaciones: {exc}"
        )

    st.divider()
    st.subheader("Resultados por material")

    st.caption(
        "Guarda los duplicados en borrador antes de enviarlos "
        "definitivamente. Los campos vacíos se conservan "
        "como pendientes."
    )

    try:
        publicadas = [
            campana
            for campana in listar_campanas()
            if campana["estado"] == "publicada"
        ]

        for campana in publicadas:
            participacion = consultar_mi_participacion(
                campana["id"]
            )

            if not participacion:
                continue

            if not participacion.get("condiciones_aceptadas"):
                continue

            if participacion.get("conflicto_interes"):
                st.warning(
                    f"{campana['codigo']}: participación bloqueada "
                    "por conflicto declarado."
                )
                continue

            ahora = datetime.now(ZONA)
            inicio_c = convertir_fecha(
                campana["fecha_apertura"]
            )
            fin_c = convertir_fecha(
                campana["fecha_cierre"]
            )

            for material in listar_materiales(campana["id"]):
                material_id = material["id"]

                with st.container(border=True):
                    st.markdown(
                        f"**{campana['codigo']} · {material['nombre']}**"
                    )

                    inicio_m = (
                        convertir_fecha(material["fecha_apertura"])
                        if material.get("fecha_apertura")
                        else inicio_c
                    )

                    fin_m = (
                        convertir_fecha(material["fecha_cierre"])
                        if material.get("fecha_cierre")
                        else fin_c
                    )

                    borrador = consultar_mi_borrador(material_id)

                    if borrador and borrador.get("estado") == "enviado":
                        st.success(
                            "Resultados enviados definitivamente. "
                            "No se pueden modificar."
                        )
                        st.caption(
                            f"Entrega ID: {borrador['id']}"
                        )
                        continue

                    if not (
                        max(inicio_c, inicio_m)
                        <= ahora
                        <= min(fin_c, fin_m)
                    ):
                        st.warning(
                            "El material está fuera de su plazo de registro."
                        )
                        continue

                    previos = {
                        int(resultado["parametro_id"]): resultado
                        for resultado in (
                            borrador or {}
                        ).get("resultados", [])
                    }

                    parametros = listar_parametros_registro(
                        material_id
                    )

                    if not parametros:
                        st.warning(
                            "Este material no tiene parámetros activos."
                        )
                        continue

                    with st.form(
                        f"pa_borrador_{campana['id']}_{material_id}"
                    ):
                        filas = []

                        for parametro in parametros:
                            parametro_id = int(parametro["id"])
                            anterior = previos.get(parametro_id, {})

                            st.markdown(
                                f"**{parametro['nombre']}** "
                                f"({parametro.get('unidad') or 'sin unidad'})"
                            )

                            r1_col, r2_col = st.columns(2)

                            resultado_1 = r1_col.text_input(
                                "Resultado 1",
                                value=str(
                                    anterior.get("resultado_1")
                                    if anterior.get("resultado_1")
                                    is not None
                                    else ""
                                ),
                                key=(
                                    f"pa_r1_{material_id}_"
                                    f"{parametro_id}"
                                ),
                            )

                            resultado_2 = r2_col.text_input(
                                "Resultado 2",
                                value=str(
                                    anterior.get("resultado_2")
                                    if anterior.get("resultado_2")
                                    is not None
                                    else ""
                                ),
                                key=(
                                    f"pa_r2_{material_id}_"
                                    f"{parametro_id}"
                                ),
                            )

                            observacion = st.text_input(
                                "Observación",
                                value=anterior.get("observacion") or "",
                                key=(
                                    f"pa_obs_{material_id}_"
                                    f"{parametro_id}"
                                ),
                            )

                            filas.append(
                                {
                                    "parametro_id": parametro_id,
                                    "resultado_1": resultado_1,
                                    "resultado_2": resultado_2,
                                    "observacion": observacion,
                                }
                            )

                        guardar_borrador = st.form_submit_button(
                            "💾 Guardar borrador",
                            type="primary",
                        )

                    if guardar_borrador:
                        try:
                            guardar_mi_borrador(
                                campana["id"],
                                material_id,
                                filas,
                            )
                            st.success(
                                "Borrador guardado correctamente."
                            )
                            st.rerun()

                        except Exception as exc:
                            st.error(
                                f"No se pudo guardar el borrador: {exc}"
                            )

                    if borrador and borrador.get("estado") == "borrador":
                        st.divider()
                        st.markdown(
                            "**Envío definitivo del material**"
                        )

                        st.warning(
                            "Después de confirmar, los resultados "
                            "quedarán bloqueados. Revisa los valores "
                            "y guarda cualquier cambio en el borrador "
                            "antes de enviarlo."
                        )

                        resultados_guardados = {
                            int(resultado["parametro_id"]): resultado
                            for resultado in borrador.get(
                                "resultados", []
                            )
                        }

                        incompletos = [
                            parametro["nombre"]
                            for parametro in parametros
                            if (
                                int(parametro["id"])
                                not in resultados_guardados
                                or resultados_guardados[
                                    int(parametro["id"])
                                ].get("resultado_1") is None
                                or resultados_guardados[
                                    int(parametro["id"])
                                ].get("resultado_2") is None
                            )
                        ]

                        if incompletos:
                            st.warning(
                                "Parámetros incompletos: "
                                + ", ".join(incompletos)
                                + ". Para enviarlos así debes justificarlo."
                            )

                        with st.form(
                            f"pa_envio_{campana['id']}_{material_id}"
                        ):
                            observacion_envio = st.text_area(
                                "Observación general del envío"
                                + (" *" if incompletos else ""),
                                max_chars=2000,
                                help=(
                                    "Obligatoria si existen parámetros "
                                    "sin los dos resultados."
                                ),
                            )

                            confirmar_envio = st.checkbox(
                                "Confirmo que revisé los resultados "
                                "guardados y autorizo el envío "
                                "definitivo sin posibilidad de edición."
                            )

                            enviar_definitivo = st.form_submit_button(
                                "📤 Enviar resultados definitivamente",
                                type="primary",
                            )

                        if enviar_definitivo:
                            try:
                                if not confirmar_envio:
                                    raise ValueError(
                                        "Marca la casilla de confirmación "
                                        "antes de enviar."
                                    )

                                if (
                                    incompletos
                                    and not observacion_envio.strip()
                                ):
                                    raise ValueError(
                                        "Debes justificar los resultados "
                                        "incompletos."
                                    )

                                entrega_id = (
                                    enviar_mis_resultados_definitivos(
                                        campana["id"],
                                        material_id,
                                        observacion_envio,
                                        confirmar_envio,
                                    )
                                )

                                st.success(
                                    "Resultados enviados definitivamente. "
                                    f"Entrega ID: {entrega_id}."
                                )
                                st.rerun()

                            except Exception as exc:
                                st.error(
                                    "No se pudo realizar el envío "
                                    f"definitivo: {exc}"
                                )

    except Exception as exc:
        st.error(
            f"No fue posible cargar los borradores: {exc}"
        )


# ============================================================
# 3. EVALUACIÓN Y DASHBOARD
# ============================================================

with tab_evaluacion:
    st.subheader("Evaluación estadística interanalistas")

    modo_simulado = st.toggle(
        "🧪 Activar simulación de 5 participantes "
        "(sin guardar en Supabase)",
        value=False,
        key="pa5_modo_simulado",
    )

    if modo_simulado:
        st.warning(
            "MODO SIMULACIÓN · Datos ficticios SIM-001 a SIM-005. "
            "No son resultados reales, no se guardan en Supabase "
            "y no son válidos para autorizar analistas."
        )

    st.caption(
        "Solo se incluyen entregas definitivas. Cada participante "
        "aporta el promedio de sus dos duplicados completos."
    )

    if not gestor:
        st.info(
            "La evaluación consolidada está reservada al líder "
            "del Laboratorio de Fábrica y a los administradores. "
            "Los analistas no pueden consultar resultados "
            "de otros participantes."
        )
    else:
        try:
            if modo_simulado:
                campanas_eval = [
                    {
                        "id": -1,
                        "codigo": "SIMULACION-5B",
                        "titulo": (
                            "Color · 5 participantes ficticios"
                        ),
                        "estado": "simulación",
                    }
                ]
            else:
                campanas_eval = listar_campanas()

            if not campanas_eval:
                st.info(
                    "No hay campañas registradas para evaluar."
                )
            else:
                opciones_c = {
                    (
                        f"{campana['codigo']} · "
                        f"{campana['titulo']} "
                        f"({campana['estado']})"
                    ): campana
                    for campana in campanas_eval
                }

                etiqueta_c = st.selectbox(
                    "Campaña",
                    list(opciones_c),
                    key="pa5_campana",
                )
                campana_eval = opciones_c[etiqueta_c]

                if modo_simulado:
                    materiales_eval = [
                        {
                            "id": -1,
                            "nombre": (
                                "AZÚCAR BLANCO (SIMULACIÓN)"
                            ),
                            "codigo_muestra": "DEMO",
                        }
                    ]
                else:
                    materiales_eval = listar_materiales(
                        campana_eval["id"]
                    )

                if not materiales_eval:
                    st.info(
                        "Esta campaña todavía no tiene materiales."
                    )
                else:
                    opciones_m = {
                        (
                            f"{material['nombre']} · "
                            f"{material.get('codigo_muestra') or 'Sin código'} "
                            f"[ID {material['id']}]"
                        ): material
                        for material in materiales_eval
                    }

                    etiqueta_m = st.selectbox(
                        "Material",
                        list(opciones_m),
                        key="pa5_material",
                    )
                    material_eval = opciones_m[etiqueta_m]

                    if modo_simulado:
                        parametros_eval = [
                            {
                                "id": -1,
                                "nombre": "Color",
                                "unidad": "UI",
                                "decimales": 2,
                            }
                        ]
                    else:
                        parametros_eval = (
                            listar_parametros_registro(
                                material_eval["id"]
                            )
                        )

                    if not parametros_eval:
                        st.warning(
                            "El material no tiene parámetros "
                            "activos para evaluar."
                        )
                    else:
                        opciones_p = {
                            (
                                f"{parametro['nombre']} "
                                f"({parametro.get('unidad') or 'sin unidad'}) "
                                f"[ID {parametro['id']}]"
                            ): parametro
                            for parametro in parametros_eval
                        }

                        etiqueta_p = st.selectbox(
                            "Parámetro",
                            list(opciones_p),
                            key="pa5_parametro",
                        )
                        parametro_eval = opciones_p[etiqueta_p]

                        st.markdown(
                            "**Desviación estándar para "
                            "evaluación (σpt)**"
                        )

                        st.caption(
                            "Debe proceder del procedimiento "
                            "estadístico aprobado. No se sustituye "
                            "automáticamente por la desviación "
                            "observada de los participantes."
                        )

                        usar_sigma = st.checkbox(
                            "Ingresar σpt para calcular "
                            "puntuaciones z",
                            value=False,
                            key="pa5_usa_sigma",
                        )

                        if modo_simulado:
                            st.caption(
                                "Para comprobar las categorías "
                                "puedes usar σpt = 5 UI SOLO "
                                "en esta simulación. No es un "
                                "valor aprobado del laboratorio."
                            )

                        sigma_eval = None

                        if usar_sigma:
                            sigma_eval = st.number_input(
                                "σpt (valor positivo, en la "
                                "unidad del parámetro)",
                                min_value=0.000000001,
                                value=(
                                    5.0
                                    if modo_simulado
                                    else 1.0
                                ),
                                format="%.8f",
                                key=(
                                    f"pa5_sigma_"
                                    f"{parametro_eval['id']}"
                                ),
                            )

                            st.warning(
                                "La σpt ingresada es temporal: "
                                "no se guarda en Supabase ni "
                                "constituye un criterio aprobado "
                                "por sí sola."
                            )

                        if st.button(
                            "📊 Generar evaluación",
                            type="primary",
                            key="pa5_generar",
                        ):
                            try:
                                if modo_simulado:
                                    reporte_nuevo = (
                                        evaluar_simulacion_color(
                                            sigma_eval
                                        )
                                    )
                                else:
                                    reporte_nuevo = evaluar_parametro(
                                        campana_eval["id"],
                                        material_eval["id"],
                                        parametro_eval["id"],
                                        sigma_eval,
                                    )

                                st.session_state[
                                    "pa5_reporte"
                                ] = reporte_nuevo

                                st.session_state[
                                    "pa5_seleccion"
                                ] = (
                                    modo_simulado,
                                    campana_eval["id"],
                                    material_eval["id"],
                                    parametro_eval["id"],
                                    sigma_eval,
                                )

                            except Exception as exc:
                                st.session_state.pop(
                                    "pa5_reporte",
                                    None,
                                )
                                st.error(
                                    "No fue posible generar "
                                    f"la evaluación: {exc}"
                                )

                        seleccion_actual = (
                            modo_simulado,
                            campana_eval["id"],
                            material_eval["id"],
                            parametro_eval["id"],
                            sigma_eval,
                        )

                        reporte = (
                            st.session_state.get("pa5_reporte")
                            if st.session_state.get(
                                "pa5_seleccion"
                            ) == seleccion_actual
                            else None
                        )

                        if reporte is not None:
                            if modo_simulado:
                                st.error(
                                    "RESULTADOS SIMULADOS — "
                                    "PROHIBIDO USO EN "
                                    "INFORMES OFICIALES"
                                )

                            decimales = max(
                                0,
                                min(
                                    int(
                                        reporte.get("decimales")
                                        or 2
                                    ),
                                    8,
                                ),
                            )

                            resultados = reporte["resultados"]

                            validos = [
                                resultado
                                for resultado in resultados
                                if resultado["promedio"] is not None
                            ]

                            a, b, c, d = st.columns(4)

                            a.metric(
                                "Entregas con resultado",
                                reporte[
                                    "participantes_con_resultados"
                                ],
                            )
                            b.metric(
                                "Duplicados completos",
                                reporte[
                                    "participantes_con_duplicados_completos"
                                ],
                            )
                            c.metric(
                                "Valor asignado · mediana",
                                formato_numero(
                                    reporte[
                                        "valor_asignado_mediana"
                                    ],
                                    decimales,
                                ),
                            )
                            d.metric(
                                "Resultados individuales válidos",
                                reporte.get(
                                    "numero_resultados_individuales",
                                    "—",
                                ),
                            )

                            st.markdown(
                                "#### Dispersión de los resultados"
                            )

                            disp1, disp2, disp3 = st.columns(3)

                            disp1.metric(
                                "Desv. observada principal · "
                                "resultados individuales",
                                formato_numero(
                                    reporte.get(
                                        "desviacion_resultados_individuales",
                                        reporte.get(
                                            "desviacion_observada_muestral"
                                        ),
                                    ),
                                    decimales,
                                ),
                            )

                            disp2.metric(
                                "Desv. secundaria · "
                                "promedios por analista",
                                formato_numero(
                                    reporte.get(
                                        "desviacion_promedios_participantes"
                                    ),
                                    decimales,
                                ),
                            )

                            disp3.metric(
                                "σpt · desviación para evaluación",
                                formato_numero(
                                    reporte.get(
                                        "desviacion_evaluacion"
                                    ),
                                    decimales,
                                ),
                            )

                            st.caption(
                                "Las dos desviaciones observadas "
                                "son muestrales y descriptivas. "
                                "La principal incluye todos los "
                                "resultados individuales válidos, "
                                "incluso si falta su duplicado; "
                                "la secundaria incluye solo "
                                "promedios de duplicados completos. "
                                "El z-score se calcula con el "
                                "promedio del participante y una "
                                "σpt independiente, que debe "
                                "justificarse documentalmente."
                            )

                            if len(validos) < 3:
                                st.warning(
                                    "Evaluación preliminar: hay "
                                    "menos de tres participantes "
                                    "con duplicados completos. "
                                    "No es suficiente para "
                                    "caracterizar de manera robusta "
                                    "el grupo; no se debe emitir "
                                    "una conclusión definitiva."
                                )

                            if (
                                reporte["desviacion_evaluacion"]
                                is None
                            ):
                                st.info(
                                    "No se han calculado z-scores "
                                    "ni categorías porque todavía "
                                    "no se ha definido σpt."
                                )

                            st.markdown(
                                "#### Resultados individuales"
                            )

                            if not resultados:
                                st.info(
                                    "Todavía no existen resultados "
                                    "enviados para este parámetro."
                                )
                            else:
                                tabla = pd.DataFrame(
                                    [
                                        {
                                            "Participante": r[
                                                "id_usuario"
                                            ],
                                            "Resultado 1": r[
                                                "resultado_1"
                                            ],
                                            "Resultado 2": r[
                                                "resultado_2"
                                            ],
                                            "Promedio": r["promedio"],
                                            "z-score": r["z_score"],
                                            "Clasificación": r[
                                                "clasificacion"
                                            ],
                                        }
                                        for r in resultados
                                    ]
                                )

                                st.dataframe(
                                    tabla,
                                    hide_index=True,
                                    use_container_width=True,
                                )

                                nombre_csv = (
                                    "SIMULACION_NO_OFICIAL_COLOR_5B.csv"
                                    if modo_simulado
                                    else (
                                        f"PA_{campana_eval['codigo']}"
                                        f"_material_{material_eval['id']}"
                                        f"_parametro_{parametro_eval['id']}.csv"
                                    )
                                )

                                st.download_button(
                                    "⬇️ Exportar resultados (CSV)",
                                    data=tabla.to_csv(
                                        index=False
                                    ).encode("utf-8-sig"),
                                    file_name=nombre_csv,
                                    mime="text/csv",
                                    key="pa5_descarga_csv",
                                )

                            if validos:
                                st.markdown(
                                    "#### Comparación de "
                                    "resultados promedio"
                                )

                                grafica = go.Figure()

                                grafica.add_trace(
                                    go.Scatter(
                                        x=[
                                            r["id_usuario"]
                                            for r in validos
                                        ],
                                        y=[
                                            r["promedio"]
                                            for r in validos
                                        ],
                                        mode="markers",
                                        name=(
                                            "Promedio por participante"
                                        ),
                                        marker=dict(size=11),
                                    )
                                )

                                asignado = reporte[
                                    "valor_asignado_mediana"
                                ]

                                grafica.add_hline(
                                    y=asignado,
                                    line_dash="dash",
                                    annotation_text=(
                                        "Mediana del grupo"
                                    ),
                                )

                                sigma = reporte[
                                    "desviacion_evaluacion"
                                ]

                                if sigma is not None:
                                    for multiplicador, estilo in [
                                        (2, "dot"),
                                        (-2, "dot"),
                                        (3, "dashdot"),
                                        (-3, "dashdot"),
                                    ]:
                                        grafica.add_hline(
                                            y=(
                                                asignado
                                                + multiplicador * sigma
                                            ),
                                            line_dash=estilo,
                                            annotation_text=(
                                                f"{multiplicador:+d} σpt"
                                            ),
                                        )

                                grafica.update_layout(
                                    xaxis_title=(
                                        "Participante (ID)"
                                    ),
                                    yaxis_title=(
                                        f"{reporte['parametro']} "
                                        f"({reporte['unidad'] or 'sin unidad'})"
                                    ),
                                    height=430,
                                    margin=dict(
                                        l=20,
                                        r=20,
                                        t=25,
                                        b=25,
                                    ),
                                )

                                st.plotly_chart(
                                    grafica,
                                    use_container_width=True,
                                )

                                if sigma is not None:
                                    st.markdown(
                                        "#### Gráfica individual "
                                        "de puntuaciones z"
                                    )

                                    st.caption(
                                        "Cada punto corresponde "
                                        "a un participante independiente. "
                                        "Las líneas horizontales "
                                        "representan los criterios "
                                        "provisionales de evaluación."
                                    )

                                    fig_z = go.Figure()

                                    colores_z = {
                                        "Satisfactorio": "#16824A",
                                        "Cuestionable": "#E3A008",
                                        "No satisfactorio": "#D64545",
                                    }

                                    for categoria, color in (
                                        colores_z.items()
                                    ):
                                        puntos = [
                                            r
                                            for r in validos
                                            if (
                                                r["clasificacion"]
                                                == categoria
                                                and r["z_score"]
                                                is not None
                                            )
                                        ]

                                        if puntos:
                                            fig_z.add_trace(
                                                go.Scatter(
                                                    x=[
                                                        r["id_usuario"]
                                                        for r in puntos
                                                    ],
                                                    y=[
                                                        r["z_score"]
                                                        for r in puntos
                                                    ],
                                                    mode="markers",
                                                    name=categoria,
                                                    marker=dict(
                                                        size=14,
                                                        color=color,
                                                        line=dict(
                                                            color="white",
                                                            width=1,
                                                        ),
                                                    ),
                                                    customdata=[
                                                        r["promedio"]
                                                        for r in puntos
                                                    ],
                                                    hovertemplate=(
                                                        "Participante: %{x}"
                                                        "<br>z = %{y:.2f}"
                                                        "<br>Promedio = "
                                                        "%{customdata:.3f}"
                                                        "<extra></extra>"
                                                    ),
                                                )
                                            )

                                    fig_z.add_hline(
                                        y=0,
                                        line_dash="solid",
                                        line_color="#65748B",
                                        annotation_text="z = 0",
                                    )

                                    for limite, estilo in [
                                        (2, "dot"),
                                        (-2, "dot"),
                                        (3, "dash"),
                                        (-3, "dash"),
                                    ]:
                                        fig_z.add_hline(
                                            y=limite,
                                            line_dash=estilo,
                                            line_color=(
                                                "#9A6D25"
                                                if abs(limite) == 2
                                                else "#B34B4B"
                                            ),
                                            annotation_text=(
                                                f"z = {limite:+d}"
                                            ),
                                        )

                                    fig_z.update_layout(
                                        xaxis_title=(
                                            "Participante (ID)"
                                        ),
                                        yaxis_title="Puntuación z",
                                        height=430,
                                        margin=dict(
                                            l=25,
                                            r=35,
                                            t=25,
                                            b=30,
                                        ),
                                        legend_title=(
                                            "Clasificación"
                                        ),
                                    )

                                    fig_z.update_xaxes(
                                        type="category",
                                        categoryorder="array",
                                        categoryarray=[
                                            r["id_usuario"]
                                            for r in validos
                                        ],
                                    )

                                    st.plotly_chart(
                                        fig_z,
                                        use_container_width=True,
                                    )

                                    st.markdown(
                                        "#### Distribución de "
                                        "clasificaciones"
                                    )

                                    conteos = pd.Series(
                                        [
                                            r["clasificacion"]
                                            for r in validos
                                        ]
                                    ).value_counts()

                                    fig_cat = go.Figure(
                                        go.Bar(
                                            x=list(conteos.index),
                                            y=list(conteos.values),
                                            text=list(conteos.values),
                                            textposition="auto",
                                        )
                                    )

                                    fig_cat.update_layout(
                                        yaxis_title="Participantes",
                                        height=320,
                                        margin=dict(
                                            l=20,
                                            r=20,
                                            t=20,
                                            b=20,
                                        ),
                                    )

                                    st.plotly_chart(
                                        fig_cat,
                                        use_container_width=True,
                                    )

                                    st.caption(
                                        "Criterio provisional: "
                                        "|z| ≤ 2 satisfactorio; "
                                        "2 < |z| < 3 cuestionable; "
                                        "|z| ≥ 3 no satisfactorio. "
                                        "Validar contra el procedimiento "
                                        "vigente antes de emitir "
                                        "informes oficiales."
                                    )
                            else:
                                st.caption(
                                    "Selecciona campaña, material "
                                    "y parámetro; luego pulsa "
                                    "«Generar evaluación»."
                                )

        except Exception as exc:
            st.error(
                "No fue posible cargar el dashboard "
                f"estadístico: {exc}"
            )


# ============================================================
# 4. INFORMES
# ============================================================

with tab_informes:
    st.subheader(
        "Informe estadístico de pruebas de aptitud"
    )

    if not gestor:
        st.info(
            "Solo el líder autorizado y los administradores "
            "pueden generar informes consolidados."
        )
    else:
        reporte_pdf = st.session_state.get(
            "pa5_reporte"
        )
        seleccion_pdf = st.session_state.get(
            "pa5_seleccion"
        )

        if reporte_pdf is None or seleccion_pdf is None:
            st.info(
                "Primero genera una evaluación en la pestaña "
                "«Evaluación y dashboard». Luego regresa "
                "aquí para obtener el PDF."
            )
        else:
            es_simulacion = bool(seleccion_pdf[0])

            if es_simulacion:
                st.warning(
                    "INFORME DE SIMULACIÓN · Datos ficticios. "
                    "No válido para decisiones sobre analistas."
                )
            else:
                st.warning(
                    "Informe preliminar. Verifica el procedimiento, "
                    "la desviación de evaluación y la suficiencia "
                    "del grupo antes de usarlo oficialmente."
                )

            st.write(
                f"**Material:** {reporte_pdf['material']} "
                f"| **Parámetro:** {reporte_pdf['parametro']}"
            )

            if st.button(
                "📄 Preparar informe PDF",
                type="primary",
                key="pa5_preparar_pdf",
            ):
                try:
                    from utils.pruebas_aptitud_informe import (
                        generar_informe_pdf,
                    )

                    st.session_state["pa5_pdf"] = (
                        generar_informe_pdf(
                            reporte_pdf,
                            es_simulacion,
                        )
                    )

                    st.session_state[
                        "pa5_pdf_origen"
                    ] = seleccion_pdf

                except Exception as exc:
                    st.session_state.pop(
                        "pa5_pdf",
                        None,
                    )
                    st.error(
                        f"No fue posible preparar el PDF: {exc}"
                    )

            if (
                st.session_state.get("pa5_pdf_origen")
                == seleccion_pdf
                and st.session_state.get("pa5_pdf")
            ):
                nombre_pdf = (
                    "PROVICHECK_Pruebas_Aptitud_SIMULACION.pdf"
                    if es_simulacion
                    else (
                        "PROVICHECK_Pruebas_Aptitud_PRELIMINAR.pdf"
                    )
                )

                st.download_button(
                    "⬇️ Descargar informe PDF",
                    data=st.session_state["pa5_pdf"],
                    file_name=nombre_pdf,
                    mime="application/pdf",
                    key="pa5_descargar_pdf",
                )

st.divider()
st.caption(
    "PROVICHECK · Pruebas de Aptitud · "
    "Comparaciones interanalistas"
)
pie_pagina()
