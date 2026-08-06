from __future__ import annotations
import pandas as pd
from database import get_connection
from utils.supabase_client import obtener_cliente_supabase

SESION_COLS = ["id","id_sesion","codigo_equipo","nombre_equipo","laboratorio","fecha","hora","responsable","usuario_login","estado","total_puntos","puntos_cumplen","puntos_no_cumplen","puntos_no_evaluados","fecha_registro"]
DETALLE_COLS = ["id","id_sesion","codigo_equipo","punto","nombre_chequeo","codigo_patron","estado_patron","fecha_vencimiento_patron","valor_nominal","resultado","error","limite_inferior","limite_superior","estado_punto","observacion","fecha_registro"]

def _df(data, cols):
    if not data:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data)
    for col in cols:
        if col not in df.columns:
            df[col] = None
    return df

def _limite(valor, defecto=20):
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        valor = defecto
    return max(1, min(valor, 100000))

def consultar_sesiones_verificacion(limite=20):
    try:
        r = (obtener_cliente_supabase().table("sesiones_verificacion")
             .select("*").order("fecha", desc=True).order("hora", desc=True)
             .limit(_limite(limite)).execute())
        return _df(r.data, SESION_COLS)
    except Exception:
        return pd.DataFrame(columns=SESION_COLS)

def consultar_detalle_sesion(id_sesion):
    if not id_sesion:
        return pd.DataFrame(columns=DETALLE_COLS)
    try:
        r = (obtener_cliente_supabase().table("detalle_verificacion")
             .select("*").eq("id_sesion", str(id_sesion).strip())
             .order("id").execute())
        return _df(r.data, DETALLE_COLS)
    except Exception:
        return pd.DataFrame(columns=DETALLE_COLS)

def consultar_ultima_verificacion(codigo_equipo):
    if not codigo_equipo:
        return pd.DataFrame(columns=SESION_COLS)
    try:
        r = (obtener_cliente_supabase().table("sesiones_verificacion")
             .select("*").eq("codigo_equipo", str(codigo_equipo).strip())
             .order("fecha", desc=True).order("hora", desc=True)
             .limit(1).execute())
        return _df(r.data, SESION_COLS)
    except Exception:
        return pd.DataFrame(columns=SESION_COLS)

def consultar_historial_equipo(codigo_equipo, limite=20):
    if not codigo_equipo:
        return pd.DataFrame(columns=SESION_COLS)
    try:
        r = (obtener_cliente_supabase().table("sesiones_verificacion")
             .select("*").eq("codigo_equipo", str(codigo_equipo).strip())
             .order("fecha", desc=True).order("hora", desc=True)
             .limit(_limite(limite)).execute())
        return _df(r.data, SESION_COLS)
    except Exception:
        return pd.DataFrame(columns=SESION_COLS)

def consultar_bitacora_equipo(codigo_equipo=None, limite=50):
    cols = ["id","fecha","hora","codigo_equipo","evento","detalle","usuario","origen","fecha_registro"]
    try:
        q = obtener_cliente_supabase().table("bitacora").select("*")
        if codigo_equipo:
            q = q.eq("codigo_equipo", str(codigo_equipo).strip())
        r = q.order("fecha", desc=True).order("hora", desc=True).limit(_limite(limite, 50)).execute()
        return _df(r.data, cols)
    except Exception:
        return pd.DataFrame(columns=cols)

def consultar_eventos_equipo(codigo_equipo, limite=20):
    return consultar_bitacora_equipo(codigo_equipo, limite)

def consultar_documentos_equipo(codigo_equipo, incluir_inactivos=False):
    columnas = [
        "id",
        "codigo_equipo",
        "tipo_documento",
        "titulo",
        "nombre_archivo",
        "ruta_archivo",
        "bucket",
        "mime_type",
        "tamano_bytes",
        "fecha_carga",
        "hora_carga",
        "fecha_emision",
        "fecha_vencimiento",
        "responsable",
        "proveedor",
        "version",
        "observaciones",
        "estado",
        "usuario_registro",
        "activo",
        "creado_en",
    ]

    try:
        consulta = (
            obtener_cliente_supabase()
            .table("documentos_equipo")
            .select("*")
            .eq("codigo_equipo", str(codigo_equipo).strip())
        )

        if not incluir_inactivos:
            consulta = consulta.eq("activo", True)

        respuesta = (
            consulta.order("fecha_carga", desc=True)
            .order("hora_carga", desc=True)
            .order("id", desc=True)
            .execute()
        )

        return _df(respuesta.data, columnas)

    except Exception:
        return pd.DataFrame(columns=columnas)


def consultar_documento_por_id(documento_id):
    try:
        respuesta = (
            obtener_cliente_supabase()
            .table("documentos_equipo")
            .select("*")
            .eq("id", int(documento_id))
            .limit(1)
            .execute()
        )

        return _df(respuesta.data, [])

    except Exception:
        return pd.DataFrame()