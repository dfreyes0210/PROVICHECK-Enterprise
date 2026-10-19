"""PROVICHECK Enterprise | Pruebas de Aptitud (fase 1: acceso y estructura).

Módulo independiente. No realiza escrituras en Supabase ni modifica datos.
"""

import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from utils.ui import aplicar_estilo, encabezado, pie_pagina, requerir_autenticacion, sidebar_pro


ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def normalizar(valor):
    texto = " ".join(str(valor or "").strip().casefold().split())
    return "".join(
        letra for letra in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(letra)
    )


def tiene_acceso(rol, laboratorio):
    """Restringe el módulo a Fábrica y a administradores globales.

    Los líderes solo acceden si están asignados a Fábrica; esto evita que
    un líder de otro laboratorio vea campañas de Fábrica por accidente.
    """
    rol_normalizado = normalizar(rol)
    lab_normalizado = normalizar(laboratorio)
    return rol_normalizado == "administrador" or lab_normalizado in {
        "fabrica", "laboratorio de fabrica", "laboratorio fabrica"
    }


def mostrar_seccion(titulo, descripcion, mensaje):
    with st.container(border=True):
        st.markdown(f"#### {titulo}")
        st.caption(descripcion)
        st.info(mensaje)


# Configuración y autenticación
st.set_page_config(
    page_title="Pruebas de Aptitud | PROVICHECK",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo()
requerir_autenticacion()

id_usuario = str(st.session_state.get("id_usuario") or "").strip()
rol = str(st.session_state.get("rol") or "").strip()
laboratorio = str(st.session_state.get("laboratorio_asignado") or "").strip()

if not id_usuario:
    st.error("No se encontró el código de usuario en la sesión. Vuelva a iniciar sesión.")
    st.stop()

if not tiene_acceso(rol, laboratorio):
    st.error("Acceso restringido al Laboratorio de Fábrica.")
    st.caption("Si considera que debe participar, solicite al administrador revisar su laboratorio asignado.")
    st.stop()

sidebar_pro()
encabezado()

st.markdown("## 🧪 Pruebas de Aptitud")
st.caption("Evaluación interanalistas · Laboratorio de Fábrica · Módulo independiente")

ahora = datetime.now(ZONA_COLOMBIA)
es_gestor = normalizar(rol) in {"administrador", "lider", "supervisor"}

col1, col2, col3 = st.columns(3)
col1.metric("Participante", id_usuario)
col2.metric("Laboratorio", "Fábrica")
col3.metric("Fecha de consulta", ahora.strftime("%d/%m/%Y"))

st.success("Acceso autorizado. Su identificación se utilizará en los registros e informes sin mostrar su nombre.")
st.warning(
    "Etapa de construcción: esta pantalla es de consulta y demostración. "
    "Todavía no crea campañas ni guarda resultados."
)

tab_inicio, tab_registro, tab_resultados, tab_informes = st.tabs(
    ["📅 Campañas", "🧪 Registrar resultados", "📊 Evaluación y dashboard", "📄 Informes"]
)

with tab_inicio:
    mostrar_seccion(
        "Pruebas activas",
        "Próximamente: material, apertura, cierre, cuenta regresiva y participantes en borrador o enviados.",
        "Aún no hay campañas conectadas a la base de datos del nuevo módulo.",
    )
    if es_gestor:
        mostrar_seccion(
            "Administración de campañas",
            "Disponible únicamente para el líder autorizado y el administrador.",
            "Próximamente: creación de campañas, materiales, parámetros y fechas de apertura y cierre.",
        )

with tab_registro:
    mostrar_seccion(
        "Registro por duplicado",
        "Cada parámetro tendrá Resultado 1, Resultado 2, promedio y diferencia.",
        "Próximamente: aceptación de condiciones, declaración de conflictos de interés, borradores y envío definitivo.",
    )
    st.caption("Los borradores no participarán en las estadísticas. El envío definitivo requerirá confirmación.")

with tab_resultados:
    mostrar_seccion(
        "Indicadores de desempeño",
        "Satisfactorios, cuestionables y no satisfactorios por material, campaña y parámetro.",
        "Los resultados grupales y el z-score permanecerán ocultos a los analistas hasta su liberación autorizada.",
    )
    if es_gestor:
        st.caption("Vista de gestión: en etapas posteriores incluirá avance de participantes y validación de resultados.")

with tab_informes:
    mostrar_seccion(
        "Informes PDF",
        "Gráficas, estadística del Excel y participantes identificados únicamente por su código.",
        "La generación de informes se habilitará después de validar los cálculos y el cierre de campañas.",
    )

st.divider()
st.caption("PROVICHECK · Pruebas de Aptitud · Fase 1: estructura y control de acceso")
pie_pagina()
