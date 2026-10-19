"""PROVICHECK Enterprise | Pruebas de Aptitud.

Fase 2A: conexión y lectura controlada de campañas.

IMPORTANTE: La conexión utiliza una clave secreta de Supabase. No se debe
exponer este cliente en el navegador ni aceptar un id_usuario, rol o
laboratorio enviados por el usuario como prueba de identidad.

La escritura de campañas y resultados se habilitará después de implementar
operaciones atómicas y comprobaciones de autorización en el servidor.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import streamlit as st

from utils.supabase_client import obtener_cliente_supabase


def _normalizar(valor: Any) -> str:
    texto = " ".join(str(valor or "").strip().casefold().split())
    return "".join(
        letra for letra in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(letra)
    )


def _identidad_sesion() -> tuple[str, str, str]:
    """Obtiene identidad exclusivamente de la sesión autenticada."""
    if st.session_state.get("autenticado") is not True:
        raise PermissionError("Debes iniciar sesión en PROVICHECK.")

    usuario = str(st.session_state.get("id_usuario") or "").strip()
    rol = _normalizar(st.session_state.get("rol"))
    laboratorio = _normalizar(st.session_state.get("laboratorio_asignado"))

    if not usuario:
        raise PermissionError("La sesión no tiene un identificador de usuario.")
    return usuario, rol, laboratorio


def _autorizar_consulta() -> str:
    usuario, rol, laboratorio = _identidad_sesion()
    if rol == "administrador":
        return usuario
    if laboratorio not in {"fabrica", "laboratorio de fabrica"}:
        raise PermissionError("El módulo es exclusivo del Laboratorio de Fábrica.")
    if rol not in {"lider", "analista"}:
        raise PermissionError("No tienes permiso para acceder a este módulo.")
    return usuario


def listar_campanas(limite: int = 100) -> list[dict[str, Any]]:
    """Consulta metadatos de campañas, sin resultados de participantes.

    No debe reutilizarse esta función para consultar respuestas confidenciales.
    """
    _autorizar_consulta()
    limite = max(1, min(int(limite), 500))
    respuesta = (
        obtener_cliente_supabase()
        .table("pa_campanas")
        .select(
            "id,codigo,titulo,descripcion,laboratorio,"
            "fecha_apertura,fecha_cierre,estado,creada_en"
        )
        .order("creada_en", desc=True)
        .limit(limite)
        .execute()
    )
    return respuesta.data or []


def listar_materiales(campana_id: int) -> list[dict[str, Any]]:
    """Consulta materiales y plazos de una campaña."""
    _autorizar_consulta()
    respuesta = (
        obtener_cliente_supabase()
        .table("pa_materiales")
        .select(
            "id,campana_id,nombre,codigo_muestra,descripcion,"
            "fecha_apertura,fecha_cierre,orden,activo"
        )
        .eq("campana_id", int(campana_id))
        .order("orden")
        .execute()
    )
    return respuesta.data or []


def listar_parametros(material_id: int) -> list[dict[str, Any]]:
    """Consulta parámetros de un material, sin resultados de participantes."""
    _autorizar_consulta()
    respuesta = (
        obtener_cliente_supabase()
        .table("pa_parametros")
        .select("id,material_id,nombre,unidad,decimales,orden,activo")
        .eq("material_id", int(material_id))
        .order("orden")
        .execute()
    )
    return respuesta.data or []


def probar_conexion_pa() -> tuple[bool, str]:
    """Verifica lectura de la nueva tabla, sin modificar datos."""
    try:
        _autorizar_consulta()
        (
            obtener_cliente_supabase()
            .table("pa_campanas")
            .select("id")
            .limit(1)
            .execute()
        )
        return True, "Conexión de lectura a Pruebas de Aptitud correcta."
    except PermissionError as exc:
        return False, str(exc)
    except Exception:
        return False, "No fue posible consultar las tablas de Pruebas de Aptitud."
