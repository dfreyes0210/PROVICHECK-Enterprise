"""PROVICHECK | Catálogos de Pruebas de Aptitud desde el Excel maestro.

Solo lectura. No modifica Excel, Supabase ni campañas existentes.
"""
from __future__ import annotations

import unicodedata
import pandas as pd
from utils.data import cargar_hoja


def _texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _normalizar(valor):
    texto = " ".join(_texto(valor).casefold().split())
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c))


def _si(valor):
    return _normalizar(valor) in {"si", "s", "true", "1", "yes"}


def _leer(hoja, columnas):
    df = cargar_hoja(hoja)
    if df.empty:
        raise ValueError(f"La hoja {hoja} no existe o no contiene registros.")
    faltantes = [col for col in columnas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {hoja}: {', '.join(faltantes)}")
    return df.fillna("")


def listar_materiales_catalogo():
    """Materiales activos, incluidos los que no fabrica Providencia."""
    df = _leer("PA_Materiales", ["ID_material", "Material", "Activo"])
    registros = []
    ids = set()
    for _, fila in df.iterrows():
        if not _si(fila["Activo"]):
            continue
        identificador = _texto(fila["ID_material"])
        nombre = _texto(fila["Material"])
        if not identificador or not nombre:
            raise ValueError("Hay materiales activos sin ID o nombre.")
        if identificador in ids:
            raise ValueError(f"ID de material duplicado: {identificador}")
        ids.add(identificador)
        registros.append({"id": identificador, "nombre": nombre})
    return registros


def listar_ensayos_catalogo(material_id, solo_providencia=True):
    """Ensayos disponibles para un material, diferenciando métodos.

    solo_providencia=True excluye registros con 'No' o 'Por definir'.
    El catálogo completo sigue disponible para futuros ingenios.
    """
    materiales = {m["id"] for m in listar_materiales_catalogo()}
    if material_id not in materiales:
        raise ValueError("El material no existe o no está activo.")

    ensayos = _leer("PA_Ensayos", ["ID_ensayo", "Ensayo", "Unidad", "Activo"])
    relaciones = _leer("PA_Material_Ensayo", [
        "ID_material", "ID_ensayo", "Método", "Habilitado Providencia"
    ])
    activos = {}
    for _, fila in ensayos.iterrows():
        if _si(fila["Activo"]):
            eid = _texto(fila["ID_ensayo"])
            if not eid or eid in activos:
                raise ValueError("Hay ID de ensayo vacío o duplicado en PA_Ensayos.")
            activos[eid] = {
                "nombre": _texto(fila["Ensayo"]),
                "unidad": _texto(fila["Unidad"]),
            }

    salida = []
    claves = set()
    for _, fila in relaciones.iterrows():
        if _texto(fila["ID_material"]) != material_id:
            continue
        eid = _texto(fila["ID_ensayo"])
        if eid not in activos:
            continue
        habilitado = _texto(fila["Habilitado Providencia"])
        if solo_providencia and not _si(habilitado):
            continue
        metodo = _texto(fila["Método"])
        if _normalizar(metodo) in {"no aplica", "n/a", "na"}:
            metodo = ""
        clave = (eid, _normalizar(metodo))
        if clave in claves:
            raise ValueError(f"Relación duplicada: {material_id}, {eid}, {metodo}")
        claves.add(clave)
        nombre = activos[eid]["nombre"]
        unidad = activos[eid]["unidad"]
        etiqueta = f"{nombre} — {metodo}" if metodo else nombre
        salida.append({
            "id": f"{material_id}|{eid}|{metodo or '-'}",
            "id_ensayo": eid,
            "nombre": nombre,
            "metodo": metodo,
            "etiqueta": etiqueta,
            "unidad": unidad,
            "decimales": 2,  # Provisional: el Excel aún no define decimales.
            "habilitado_providencia": _si(habilitado),
        })
    return salida


def preparar_parametros_campana(ensayos_seleccionados):
    """Adapta los ensayos al formato actual de la RPC de Supabase.

    El método se incorpora al nombre para no perderlo: 'Humedad - Método A'.
    No se altera el esquema de pa_parametros.
    """
    parametros = []
    nombres = set()
    for ensayo in ensayos_seleccionados:
        nombre = ensayo["etiqueta"].replace(" — ", " - ").strip()
        if _normalizar(nombre) in nombres:
            raise ValueError(f"Parámetro duplicado: {nombre}")
        nombres.add(_normalizar(nombre))
        parametros.append({
            "nombre": nombre,
            "unidad": ensayo["unidad"],
            "decimales": ensayo.get("decimales", 2),
        })

    return parametros