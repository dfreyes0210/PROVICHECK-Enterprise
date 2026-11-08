"""PROVICHECK | Campañas de Pruebas de Aptitud. Uso exclusivo en servidor."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation
import unicodedata
import streamlit as st
from utils.supabase_client import obtener_cliente_supabase

LABS = {'fabrica', 'laboratorio de fabrica', 'laboratorio fabrica'}

def normalizar(v):
    t = ' '.join(str(v or '').casefold().split())
    return ''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c))

def identidad(gestor=False):
    if st.session_state.get('autenticado') is not True:
        raise PermissionError('Inicia sesión en PROVICHECK.')
    usuario = str(st.session_state.get('id_usuario') or '').strip()
    rol = normalizar(st.session_state.get('rol'))
    lab = normalizar(st.session_state.get('laboratorio_asignado'))
    if not usuario:
        raise PermissionError('No se identificó al usuario.')
    if gestor:
        permitido = rol == 'administrador' or (rol == 'lider' and lab in LABS)
    else:
        permitido = rol == 'administrador' or (rol in {'lider', 'analista'} and lab in LABS)
    if not permitido:
        raise PermissionError('No estás autorizado para esta operación.')
    return usuario

def listar_campanas(limite=100):
    identidad()
    r = (obtener_cliente_supabase().table('pa_campanas')
         .select('id,codigo,titulo,descripcion,fecha_apertura,fecha_cierre,estado')
         .order('id', desc=True).limit(min(max(int(limite),1),500)).execute())
    return r.data or []

def listar_materiales(campana_id):
    identidad()
    r = (obtener_cliente_supabase().table('pa_materiales')
         .select('id,nombre,codigo_muestra,fecha_apertura,fecha_cierre')
         .eq('campana_id', int(campana_id)).order('orden').execute())
    return r.data or []

def listar_parametros(material_id):
    identidad()
    r = (obtener_cliente_supabase().table('pa_parametros')
         .select('nombre,unidad,decimales').eq('material_id',int(material_id))
         .order('orden').execute())
    return r.data or []

def probar_conexion_pa():
    try:
        listar_campanas(1)
        return True, 'Conexión de lectura correcta.'
    except Exception as exc:
        return False, str(exc)

def crear_campana_borrador(datos):
    actor = identidad(gestor=True)
    codigo = str(datos.get('codigo') or '').strip()
    titulo = str(datos.get('titulo') or '').strip()
    inicio, fin = datos.get('fecha_apertura'), datos.get('fecha_cierre')
    if not codigo or not titulo:
        raise ValueError('Código y título son obligatorios.')
    if not isinstance(inicio, datetime) or not isinstance(fin, datetime) or inicio.tzinfo is None or fin.tzinfo is None or fin <= inicio:
        raise ValueError('Periodo general inválido.')
    materiales = datos.get('materiales') or []
    if not materiales:
        raise ValueError('Agrega al menos un material.')
    usados = set()
    payload_mat = []
    for m in materiales:
        nombre = str(m.get('nombre') or '').strip()
        if not nombre or normalizar(nombre) in usados:
            raise ValueError('Los materiales requieren nombres diferentes.')
        usados.add(normalizar(nombre))
        mi, mf = m.get('fecha_apertura'), m.get('fecha_cierre')
        if (mi is None) != (mf is None) or (mi is not None and not (inicio <= mi < mf <= fin)):
            raise ValueError(f'Fechas particulares inválidas en {nombre}.')
        pars = m.get('parametros') or []
        if not pars:
            raise ValueError(f'Faltan parámetros en {nombre}.')
        nombres_par = set()
        payload_par = []
        for p in pars:
            pn = str(p.get('nombre') or '').strip()
            if not pn or normalizar(pn) in nombres_par:
                raise ValueError(f'Parámetro vacío o repetido en {nombre}.')
            nombres_par.add(normalizar(pn))
            try:
                dec = int(p.get('decimales', 2))
            except (ValueError, TypeError) as exc:
                raise ValueError(f'Decimales inválidos para {pn}.') from exc
            if not 0 <= dec <= 8:
                raise ValueError('Los decimales deben estar entre 0 y 8.')
            payload_par.append({'nombre':pn,'unidad':str(p.get('unidad') or '').strip(),'decimales':dec})
        payload_mat.append({'nombre':nombre,'codigo_muestra':str(m.get('codigo_muestra') or '').strip(),
                            'descripcion':str(m.get('descripcion') or '').strip(),
                            'fecha_apertura':mi.isoformat() if mi else None,
                            'fecha_cierre':mf.isoformat() if mf else None,'parametros':payload_par})
    payload = {'codigo':codigo,'titulo':titulo,'descripcion':str(datos.get('descripcion') or '').strip(),
               'fecha_apertura':inicio.isoformat(),'fecha_cierre':fin.isoformat(),'materiales':payload_mat}
    r = obtener_cliente_supabase().rpc('pa_crear_campana_borrador', {'p_datos':payload,'p_actor':actor}).execute()
    if r.data is None:
        raise RuntimeError('Supabase no devolvió el ID de campaña.')
    return int(r.data)

def publicar_campana(campana_id):
    """Publicación atómica; la función SQL comprueba estado, contenido y registra auditoría."""
    actor = identidad(gestor=True)
    try:
        identificador = int(campana_id)
    except (ValueError, TypeError) as exc:
        raise ValueError('Identificador de campaña inválido.') from exc
    if identificador <= 0:
        raise ValueError('Identificador de campaña inválido.')
    r = obtener_cliente_supabase().rpc('pa_publicar_campana', {
        'p_campana_id': identificador, 'p_actor': actor
    }).execute()
    if r.data is not True:
        raise RuntimeError('Supabase no confirmó la publicación.')
    return True

def consultar_mi_participacion(campana_id):
    """Consulta exclusivamente la declaración del usuario de la sesión."""
    actor = identidad()
    r = (obtener_cliente_supabase().table('pa_participaciones')
         .select('id,campana_id,condiciones_aceptadas,fecha_aceptacion,conflicto_interes,declaracion_impedimento')
         .eq('campana_id', int(campana_id))
         .eq('id_usuario', actor)
         .limit(1).execute())
    return r.data[0] if r.data else None

def registrar_mi_participacion(campana_id, condiciones_aceptadas, conflicto_interes, declaracion=''):
    """Registro único e irreversible en fase 3B; identidad derivada de sesión."""
    actor = identidad()
    if condiciones_aceptadas is not True:
        raise ValueError('Debes aceptar las condiciones de participación.')
    if type(conflicto_interes) is not bool:
        raise ValueError('Debes declarar expresamente si existe conflicto de interés.')
    detalle = str(declaracion or '').strip()
    if conflicto_interes and not detalle:
        raise ValueError('Describe el posible conflicto de interés.')
    try:
        cid = int(campana_id)
    except (TypeError, ValueError) as exc:
        raise ValueError('Campaña inválida.') from exc
    if cid <= 0:
        raise ValueError('Campaña inválida.')
    r = obtener_cliente_supabase().rpc('pa_registrar_participacion', {
        'p_campana_id': cid,
        'p_actor': actor,
        'p_conflicto': conflicto_interes,
        'p_declaracion': detalle if conflicto_interes else None,
    }).execute()
    if r.data is None:
        raise RuntimeError('Supabase no confirmó la participación.')
    return int(r.data)

def listar_parametros_registro(material_id):
    """Devuelve identificadores y configuración para el formulario de resultados."""
    identidad()
    mid = int(material_id)
    if mid <= 0:
        raise ValueError('Material inválido.')
    respuesta = (obtener_cliente_supabase().table('pa_parametros')
                 .select('id,material_id,nombre,unidad,decimales,orden,activo')
                 .eq('material_id', mid).eq('activo', True)
                 .order('orden').execute())
    return respuesta.data or []


def consultar_mi_borrador(material_id):
    """Consulta la entrega propia sin mostrar resultados de otros participantes."""
    actor = identidad()
    mid = int(material_id)
    if mid <= 0:
        raise ValueError('Material inválido.')
    material = (obtener_cliente_supabase().table('pa_materiales')
                .select('id,campana_id').eq('id', mid).limit(1).execute())
    if not material.data:
        raise ValueError('Material no encontrado.')
    cid = material.data[0]['campana_id']
    participacion = (obtener_cliente_supabase().table('pa_participaciones')
                     .select('id').eq('campana_id', cid)
                     .eq('id_usuario', actor).limit(1).execute())
    if not participacion.data:
        return None
    entrega = (obtener_cliente_supabase().table('pa_entregas_material')
               .select('id,estado,material_id,actualizado_en')
               .eq('participacion_id', participacion.data[0]['id'])
               .eq('material_id', mid).limit(1).execute())
    if not entrega.data:
        return None
    datos = entrega.data[0]
    resultados = (obtener_cliente_supabase().table('pa_resultados')
                  .select('parametro_id,resultado_1,resultado_2,promedio,observacion')
                  .eq('entrega_id', datos['id']).execute())
    return {**datos, 'resultados': resultados.data or []}


def guardar_mi_borrador(campana_id, material_id, resultados):
    """Envía un borrador atómico a la RPC; el actor procede de la sesión."""
    actor = identidad()
    cid, mid = int(campana_id), int(material_id)
    if cid <= 0 or mid <= 0:
        raise ValueError('Campaña o material inválido.')
    if not isinstance(resultados, list) or not 1 <= len(resultados) <= 100:
        raise ValueError('Debes enviar entre 1 y 100 parámetros.')
    payload = []
    ids = set()
    for fila in resultados:
        pid = int(fila['parametro_id'])
        if pid <= 0 or pid in ids:
            raise ValueError('Parámetros inválidos o repetidos.')
        ids.add(pid)
        registro = {'parametro_id': pid}
        for campo in ('resultado_1', 'resultado_2'):
            valor = fila.get(campo)
            if valor is None or str(valor).strip() == '':
                registro[campo] = None
            else:
                try:
                    numero = Decimal(str(valor).strip())
                except (InvalidOperation, ValueError) as exc:
                    raise ValueError(f'{campo} debe ser numérico.') from exc
                if not numero.is_finite():
                    raise ValueError(f'{campo} debe ser finito.')
                registro[campo] = float(numero)
        observacion = str(fila.get('observacion') or '').strip()
        if len(observacion) > 2000:
            raise ValueError('Observación demasiado extensa.')
        registro['observacion'] = observacion
        payload.append(registro)
    respuesta = obtener_cliente_supabase().rpc('pa_guardar_borrador_resultados', {
        'p_campana_id': cid, 'p_material_id': mid,
        'p_actor': actor, 'p_resultados': payload,
    }).execute()
    if respuesta.data is None:
        raise RuntimeError('Supabase no confirmó el guardado.')
    return int(respuesta.data)

def enviar_mis_resultados_definitivos(campana_id, material_id, observacion='', confirmacion=False):
    """Envía definitivamente los resultados del usuario autenticado."""

    actor = identidad()

    if confirmacion is not True:
        raise ValueError('Debes confirmar expresamente el envío definitivo.')

    try:
        cid = int(campana_id)
        mid = int(material_id)
    except (ValueError, TypeError) as exc:
        raise ValueError('Campaña o material inválido.') from exc

    if cid <= 0 or mid <= 0:
        raise ValueError('Campaña o material inválido.')

    obs = str(observacion or '').strip()

    if len(obs) > 2000:
        raise ValueError('La observación no puede superar 2000 caracteres.')

    respuesta = obtener_cliente_supabase().rpc(
        'pa_enviar_resultados_definitivos',
        {
            'p_campana_id': cid,
            'p_material_id': mid,
            'p_actor': actor,
            'p_observacion': obs or None,
            'p_confirmacion': True,
        }
    ).execute()

    if respuesta.data is None:
        raise RuntimeError('Supabase no confirmó el envío definitivo.')

    return int(respuesta.data)
