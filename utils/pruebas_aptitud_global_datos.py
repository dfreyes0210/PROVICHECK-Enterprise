"""PROVICHECK | Preparación de informe global PA. Solo lectura, acceso gestor."""
from __future__ import annotations
import re
import unicodedata
from collections import defaultdict
from statistics import median, stdev
from utils.pruebas_aptitud_db import identidad, listar_materiales, listar_parametros_registro
from utils.supabase_client import obtener_cliente_supabase
from utils.data import cargar_hoja
from utils.pruebas_aptitud_estadistica import evaluar_parametro

METODOS = {
    'cenicana': 'Referencia interlaboratorio Cenicaña 2026',
    'individuales': 'Desviación estándar de resultados individuales',
    'promedios': 'Desviación estándar de promedios por analista',
}

def normalizar(v):
    s = ' '.join(str(v or '').casefold().split())
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def _nombre_ensayo(nombre):
    s = normalizar(nombre)
    s = re.sub(r'\s*[-–—]\s*metodo\s*[ab]\s*$', '', s)
    if s in ('pol', 'pol aparente', 'polarizacion aparente'):
        return 'polarizacion'
    return s

def _metodo_ensayo(nombre):
    m = re.search(r'm[eé]todo\s*([ab])\s*$', str(nombre), re.I)
    return f'Método {m.group(1).upper()}' if m else ''

def _referencias():
    df = cargar_hoja('PA_Desviaciones')
    obligatorias = {'Año','Material','Parámetro','Método','σpt','Unidad'}
    if df.empty or not obligatorias.issubset(df.columns):
        raise ValueError('PA_Desviaciones está vacía o le faltan columnas requeridas.')
    return df.to_dict('records')

def _referencia(material, parametro, unidad, refs):
    nombre = _nombre_ensayo(parametro)
    metodo = normalizar(_metodo_ensayo(parametro))
    candidatos = []
    for r in refs:
        try:
            if int(r['Año']) != 2026: continue
            if normalizar(r['Material']) != normalizar(material): continue
            if _nombre_ensayo(r['Parámetro']) != nombre: continue
            if normalizar(r.get('Método')) not in (metodo, 'no aplica', ''): continue
            if normalizar(r.get('Unidad')) != normalizar(unidad): continue
            v = float(r['σpt'])
            if v > 0: candidatos.append(v)
        except (ValueError, TypeError, OverflowError):
            continue
    if len(candidatos) != 1:
        raise ValueError(f'Referencia Cenicaña no única o ausente: {material} / {parametro} ({unidad}). Coincidencias: {len(candidatos)}')
    return candidatos[0]

def preparar_informe_global(campana, metodo):
    """Devuelve datos anonimizados para el PDF y relación confidencial separada."""
    identidad(gestor=True)
    if metodo not in METODOS: raise ValueError('Metodología no reconocida.')
    cid = int(campana['id'])
    db = obtener_cliente_supabase()
    participaciones = (db.table('pa_participaciones').select('id,id_usuario')
                       .eq('campana_id', cid).order('id').execute()).data or []
    # Identificadores estables dentro de la campaña, nunca nombres en resultados.
    mapa = {str(p['id_usuario']): f'PA-{i:03d}' for i,p in enumerate(participaciones, 1)}
    usuarios_df = cargar_hoja('Usuarios')
    nombres = {}
    if not usuarios_df.empty and {'id_usuario','nombre_usuario'}.issubset(usuarios_df.columns):
        nombres = {str(r['id_usuario']).strip():str(r['nombre_usuario']).strip()
                   for r in usuarios_df.to_dict('records')}
    lista_nombres = [nombres.get(u, 'Participante registrado') for u in mapa]
    confidencial = [{'codigo':codigo,'id_usuario':usuario,'nombre':nombres.get(usuario,'No disponible')}
                    for usuario,codigo in mapa.items()]
    refs = _referencias() if metodo == 'cenicana' else []
    materiales = []
    advertencias = []
    for material in listar_materiales(cid):
        ensayos = []
        for parametro in listar_parametros_registro(material['id']):
            reporte = evaluar_parametro(cid, material['id'], parametro['id'], None)
            if metodo == 'cenicana':
                try: sigma = _referencia(material['nombre'], parametro['nombre'], parametro.get('unidad',''), refs)
                except ValueError as e:
                    sigma = None
                    advertencias.append(str(e))
            elif metodo == 'individuales':
                sigma = reporte['desviacion_resultados_individuales']
            else:
                sigma = reporte['desviacion_promedios_participantes']
            if sigma is not None and sigma > 0:
                # Se reutiliza el motor para mantener idéntica clasificación.
                reporte = evaluar_parametro(cid, material['id'], parametro['id'], sigma)
            else:
                sigma = None
                advertencias.append(f'Sin dispersión válida: {material["nombre"]} / {parametro["nombre"]}')
            filas = []
            for fila in reporte['resultados']:
                usuario = fila.get('id_usuario')
                if usuario not in mapa:
                    raise ValueError('Resultado sin participación registrada en campaña.')
                filas.append({k:v for k,v in fila.items() if k != 'id_usuario'} |
                            {'codigo_anonimo': mapa[usuario]})
            reporte['resultados'] = filas
            reporte['sigma_pt_aprobada'] = bool(sigma)  # Solo habilita z en el PDF PRELIMINAR; NO es aprobación formal.
            reporte['metodologia_sigma'] = METODOS[metodo]
            # El generador existente oculta las puntuaciones hasta aprobación.
            ensayos.append(reporte)
        materiales.append({'nombre': material['nombre'], 'ensayos': ensayos})
    datos_campana = {k:campana.get(k) for k in ('codigo','titulo','fecha_apertura','fecha_cierre')}
    datos_campana['metodologia_sigma'] = METODOS[metodo]
    return datos_campana, materiales, lista_nombres, confidencial, advertencias
