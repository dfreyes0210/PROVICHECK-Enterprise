from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


@st.cache_resource(show_spinner=False)
def obtener_cliente_supabase() -> Client:
    """
    Crea y reutiliza una única conexión con Supabase.

    Las credenciales se leen desde Streamlit Secrets y nunca
    deben escribirse dentro del repositorio de GitHub.
    """
    try:
        url = str(st.secrets["supabase"]["url"]).strip()
        key = str(st.secrets["supabase"]["key"]).strip()
    except KeyError as exc:
        raise RuntimeError(
            "No se encontraron las credenciales de Supabase "
            "en Streamlit Secrets."
        ) from exc

    if not url or not key:
        raise RuntimeError(
            "La URL o la clave de Supabase están vacías."
        )

    return create_client(url, key)


def probar_conexion_supabase() -> tuple[bool, str, list]:
    """
    Comprueba que PROVICHECK pueda consultar la tabla
    sesiones_verificacion.
    """
    try:
        cliente = obtener_cliente_supabase()

        respuesta = (
            cliente.table("sesiones_verificacion")
            .select("id_sesion")
            .limit(1)
            .execute()
        )

        return (
            True,
            "Conexión con Supabase establecida correctamente.",
            respuesta.data or [],
        )

    except Exception as exc:
        return (
            False,
            f"No fue posible conectar con Supabase: {exc}",
            [],
        )