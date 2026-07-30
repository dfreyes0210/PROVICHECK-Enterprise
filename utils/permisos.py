import unicodedata

import pandas as pd
import streamlit as st


ROLES_GLOBALES = {"Administrador", "Líder"}


def _texto_seguro(valor):
    if valor is None:
        return ""

    texto = str(valor).strip()
    if texto.lower() in {"nan", "nat", "none"}:
        return ""

    return texto


def _normalizar_comparacion(valor):
    """
    Normaliza únicamente para comparar con seguridad:
    elimina espacios repetidos, diferencias de mayúsculas y tildes.
    Los nombres originales continúan mostrándose tal como están en Excel.
    """
    texto = " ".join(_texto_seguro(valor).split()).casefold()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def _normalizar_rol(valor):
    rol = _normalizar_comparacion(valor)

    equivalencias = {
        "administrador": "Administrador",
        "admin": "Administrador",
        "lider": "Líder",
        "supervisor": "Líder",
        "analista": "Analista",
    }

    return equivalencias.get(
        rol,
        _texto_seguro(valor) or "Analista",
    )


def obtener_rol_usuario():
    return _normalizar_rol(st.session_state.get("rol"))


def obtener_laboratorio_usuario():
    return _texto_seguro(
        st.session_state.get("laboratorio_asignado")
    )


def usuario_tiene_acceso_global():
    return obtener_rol_usuario() in ROLES_GLOBALES


def obtener_equipos_permitidos(equipos):
    """
    Devuelve los equipos que el usuario puede verificar.

    Administrador y Líder:
        reciben todos los equipos.

    Analista:
        recibe únicamente los equipos cuyo laboratorio coincide con
        laboratorio_asignado de su sesión.
    """
    if equipos is None:
        return pd.DataFrame()

    df = equipos.copy()

    if df.empty:
        return df

    if usuario_tiene_acceso_global():
        return df.reset_index(drop=True)

    if "laboratorio" not in df.columns:
        return df.iloc[0:0].copy()

    laboratorio_usuario = obtener_laboratorio_usuario()
    laboratorio_normalizado = _normalizar_comparacion(
        laboratorio_usuario
    )

    if not laboratorio_normalizado:
        return df.iloc[0:0].copy()

    mascara = df["laboratorio"].apply(
        _normalizar_comparacion
    ).eq(laboratorio_normalizado)

    return df.loc[mascara].reset_index(drop=True)


def puede_verificar_equipo(equipo):
    """
    Valida nuevamente el permiso antes de guardar.

    Retorna:
        (True, mensaje) cuando está autorizado.
        (False, motivo) cuando debe bloquearse.
    """
    if usuario_tiene_acceso_global():
        return True, "Acceso global autorizado."

    if equipo is None:
        return False, "No fue posible identificar el equipo."

    if hasattr(equipo, "to_dict"):
        equipo = equipo.to_dict()

    if not isinstance(equipo, dict):
        return False, "La información del equipo no es válida."

    laboratorio_equipo = _texto_seguro(
        equipo.get("laboratorio")
    )
    laboratorio_usuario = obtener_laboratorio_usuario()

    if not laboratorio_usuario:
        return (
            False,
            "El usuario no tiene un laboratorio asignado.",
        )

    if not laboratorio_equipo:
        return (
            False,
            "El equipo no tiene laboratorio definido en la base maestra.",
        )

    coincide = (
        _normalizar_comparacion(laboratorio_equipo)
        == _normalizar_comparacion(laboratorio_usuario)
    )

    if not coincide:
        codigo = _texto_seguro(
            equipo.get("codigo_equipo")
        ) or "Sin código"

        return (
            False,
            f"El equipo {codigo} pertenece a "
            f"'{laboratorio_equipo}' y su usuario está asignado a "
            f"'{laboratorio_usuario}'.",
        )

    return True, "Equipo autorizado para el laboratorio del usuario."