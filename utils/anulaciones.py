from __future__ import annotations
from datetime import datetime
import streamlit as st
from utils.permisos import obtener_rol_usuario
from utils.supabase_client import obtener_cliente_supabase

ROLES_AUTORIZADOS_ANULACION = {"Administrador", "Líder"}

def _texto(v):
    if v is None: return ""
    t=str(v).strip()
    return "" if t.lower() in {"nan","nat","none"} else t

def _usuario_actual():
    for k in ("nombre_usuario","usuario_nombre","usuario_login","usuario","nombre"):
        v=_texto(st.session_state.get(k))
        if v: return v
    return "Usuario no identificado"

def puede_anular_verificaciones():
    return obtener_rol_usuario() in ROLES_AUTORIZADOS_ANULACION

def validar_permiso_anulacion():
    rol=obtener_rol_usuario()
    if rol not in ROLES_AUTORIZADOS_ANULACION:
        return False, "Solo los roles Administrador y Líder pueden anular verificaciones."
    return True, f"Anulación autorizada para el rol {rol}."

def _validar_motivo(motivo):
    motivo=_texto(motivo)
    if len(motivo)<10:
        return False, "Debe registrar un motivo claro de al menos 10 caracteres."
    return True, motivo

def _obtener_sesion(id_sesion):
    r=(obtener_cliente_supabase().table("sesiones_verificacion").select("*")
       .eq("id_sesion",_texto(id_sesion)).limit(1).execute())
    return (r.data or [None])[0]

def _obtener_detalle(id_detalle):
    r=(obtener_cliente_supabase().table("detalle_verificacion").select("*")
       .eq("id",int(id_detalle)).limit(1).execute())
    return (r.data or [None])[0]

def _auditoria(id_sesion,codigo_equipo,tipo,punto,motivo,usuario,anterior,observacion=""):
    obtener_cliente_supabase().table("anulaciones_verificacion").insert({
        "id_sesion":_texto(id_sesion),"codigo_equipo":_texto(codigo_equipo),
        "tipo_anulacion":tipo,"punto":_texto(punto) or None,
        "motivo":motivo,"usuario":usuario,"estado_anterior":anterior,
        "estado_nuevo":"Anulado","observacion":_texto(observacion) or None
    }).execute()

def _bitacora(codigo,event,detalle,usuario):
    ahora=datetime.now()
    try:
        obtener_cliente_supabase().table("bitacora").insert({
            "fecha":ahora.date().isoformat(),"hora":ahora.strftime("%H:%M:%S"),
            "codigo_equipo":codigo,"evento":event,"detalle":detalle,
            "usuario":usuario,"origen":"Anulaciones"
        }).execute()
    except Exception:
        pass

def anular_punto(id_detalle,motivo,observacion=""):
    ok,msg=validar_permiso_anulacion()
    if not ok: return False,msg
    ok,motivo=_validar_motivo(motivo)
    if not ok: return False,motivo
    try:
        d=_obtener_detalle(id_detalle)
        if not d: return False,"No se encontró el punto seleccionado."
        if bool(d.get("anulado")): return False,"Este punto ya está anulado."
        ses=_obtener_sesion(d.get("id_sesion"))
        if not ses: return False,"No se encontró la sesión asociada."
        if bool(ses.get("anulada")): return False,"La sesión completa ya está anulada."
        usuario=_usuario_actual(); ahora=datetime.now().astimezone().isoformat()
        anterior=_texto(d.get("estado_registro")) or "Válido"
        (obtener_cliente_supabase().table("detalle_verificacion").update({
            "estado_registro":"Anulado","anulado":True,"fecha_anulacion":ahora,
            "anulado_por":usuario,"motivo_anulacion":motivo
        }).eq("id",int(id_detalle)).execute())
        _auditoria(d.get("id_sesion"),d.get("codigo_equipo"),"Punto",
                   d.get("punto"),motivo,usuario,anterior,observacion)
        _bitacora(_texto(d.get("codigo_equipo")),"Punto de verificación anulado",
                  f"Sesión {_texto(d.get('id_sesion'))}. Punto: {_texto(d.get('punto'))}. Motivo: {motivo}",usuario)
        return True,f"Punto '{_texto(d.get('punto'))}' anulado. El registro original se conserva."
    except Exception as exc:
        return False,f"No fue posible anular el punto: {exc}"

def anular_sesion(id_sesion,motivo,observacion=""):
    ok,msg=validar_permiso_anulacion()
    if not ok: return False,msg
    ok,motivo=_validar_motivo(motivo)
    if not ok: return False,motivo
    id_sesion=_texto(id_sesion)
    if not id_sesion: return False,"No se recibió un ID de sesión válido."
    try:
        ses=_obtener_sesion(id_sesion)
        if not ses: return False,"No se encontró la sesión seleccionada."
        if bool(ses.get("anulada")): return False,"Esta sesión ya está anulada."
        usuario=_usuario_actual(); ahora=datetime.now().astimezone().isoformat()
        codigo=_texto(ses.get("codigo_equipo"))
        anterior=_texto(ses.get("estado_registro")) or "Válida"
        cli=obtener_cliente_supabase()
        cli.table("sesiones_verificacion").update({
            "estado_registro":"Anulada","anulada":True,"fecha_anulacion":ahora,
            "anulada_por":usuario,"motivo_anulacion":motivo
        }).eq("id_sesion",id_sesion).execute()
        cli.table("detalle_verificacion").update({
            "estado_registro":"Anulado","anulado":True,"fecha_anulacion":ahora,
            "anulado_por":usuario,"motivo_anulacion":motivo
        }).eq("id_sesion",id_sesion).execute()
        _auditoria(id_sesion,codigo,"Sesión","",motivo,usuario,anterior,observacion)
        _bitacora(codigo,"Sesión de verificación anulada",
                  f"Sesión {id_sesion}. Motivo: {motivo}",usuario)
        return True,f"Sesión {id_sesion} anulada. Los registros originales permanecen conservados."
    except Exception as exc:
        return False,f"No fue posible anular la sesión: {exc}"