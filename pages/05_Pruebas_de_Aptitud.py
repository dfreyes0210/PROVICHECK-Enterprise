"""PROVICHECK | Pruebas de Aptitud, creación de campañas multimaterial."""
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
from utils.ui import aplicar_estilo, encabezado, pie_pagina, requerir_autenticacion, sidebar_pro
from utils.pruebas_aptitud_db import listar_campanas, listar_materiales, listar_parametros, crear_campana_borrador

ZONA = ZoneInfo('America/Bogota')

def norm(v):
    t = ' '.join(str(v or '').casefold().split())
    return ''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c))

def fecha(d, h):
    return datetime.combine(d, h, tzinfo=ZONA)

def mostrar_fecha(iso):
    if not iso:
        return 'Plazo general'
    return datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(ZONA).strftime('%d/%m/%Y %H:%M')

st.set_page_config(page_title='Pruebas de Aptitud | PROVICHECK', page_icon='🧪', layout='wide')
aplicar_estilo()
requerir_autenticacion()
usuario = str(st.session_state.get('id_usuario') or '').strip()
rol = norm(st.session_state.get('rol'))
lab = norm(st.session_state.get('laboratorio_asignado'))
lab_ok = lab in {'fabrica','laboratorio de fabrica','laboratorio fabrica'}
if st.session_state.get('autenticado') is not True or not usuario or not (rol == 'administrador' or (lab_ok and rol in {'lider','analista'})):
    st.error('Acceso restringido al Laboratorio de Fábrica.')
    st.stop()
gestor = rol == 'administrador' or (rol == 'lider' and lab_ok)
sidebar_pro()
encabezado()
st.markdown('## 🧪 Pruebas de Aptitud')
st.caption('Evaluación interanalistas · Laboratorio de Fábrica')
a,b,c = st.columns(3)
a.metric('Participante',usuario)
b.metric('Laboratorio','Fábrica')
c.metric('Fecha',datetime.now(ZONA).strftime('%d/%m/%Y'))
st.info('Etapa 2: creación de campañas en borrador. Registro de resultados aún no habilitado.')

t1,t2,t3,t4 = st.tabs(['📅 Campañas','🧪 Registrar resultados','📊 Evaluación y dashboard','📄 Informes'])
with t1:
    st.subheader('Campañas registradas')
    try:
        campanas = listar_campanas()
        if not campanas:
            st.info('Todavía no hay campañas registradas.')
        for camp in campanas:
            with st.expander(f"{camp['codigo']} · {camp['titulo']} · {camp['estado']}"):
                st.write(f"Apertura: {mostrar_fecha(camp['fecha_apertura'])} | Cierre: {mostrar_fecha(camp['fecha_cierre'])}")
                for mat in listar_materiales(camp['id']):
                    st.markdown(f"**{mat['nombre']}**")
                    if mat.get('fecha_apertura'):
                        st.caption(f"Plazo particular: {mostrar_fecha(mat['fecha_apertura'])} a {mostrar_fecha(mat['fecha_cierre'])}")
                    pars = listar_parametros(mat['id'])
                    st.caption('Parámetros: ' + ', '.join(p['nombre'] for p in pars))
    except Exception as exc:
        st.error(f'Error consultando campañas: {exc}')

    if gestor:
        st.divider()
        st.subheader('Crear campaña en borrador')
        if 'pa_nmateriales' not in st.session_state:
            st.session_state.pa_nmateriales = 1
        with st.form('pa_formulario'):
            col1,col2 = st.columns([1,2])
            codigo = col1.text_input('Código de campaña *', placeholder='PA-2026-001')
            titulo = col2.text_input('Título *')
            descripcion = st.text_area('Descripción',height=70)
            d1,h1,d2,h2 = st.columns(4)
            hoy = datetime.now(ZONA).date()
            apertura_d = d1.date_input('Apertura general',value=hoy)
            apertura_h = h1.time_input('Hora apertura',value=time(8,0))
            cierre_d = d2.date_input('Cierre general',value=hoy+timedelta(days=7))
            cierre_h = h2.time_input('Hora cierre',value=time(17,0))
            materiales = []
            for i in range(st.session_state.pa_nmateriales):
                with st.container(border=True):
                    st.markdown(f'**Material {i+1}**')
                    m1,m2 = st.columns(2)
                    nombre = m1.text_input('Material *',key=f'pa_nombre_{i}',placeholder='Azúcar blanco')
                    muestra = m2.text_input('Código de muestra',key=f'pa_muestra_{i}')
                    mdesc = st.text_input('Descripción del material',key=f'pa_descripcion_{i}')
                    particular = st.checkbox('Fechas particulares para este material',key=f'pa_particular_{i}')
                    mi = mf = None
                    if particular:
                        x1,x2,x3,x4 = st.columns(4)
                        mi = fecha(x1.date_input('Apertura',value=apertura_d,key=f'pa_mi_d_{i}'),
                                   x2.time_input('Hora',value=apertura_h,key=f'pa_mi_h_{i}'))
                        mf = fecha(x3.date_input('Cierre',value=cierre_d,key=f'pa_mf_d_{i}'),
                                   x4.time_input('Hora',value=cierre_h,key=f'pa_mf_h_{i}'))
                    st.caption('Un parámetro por línea: Nombre | Unidad | Decimales (ejemplo: Color | UI | 0)')
                    lineas = st.text_area('Parámetros *',key=f'pa_pars_{i}',height=100,
                                           placeholder='Color | UI | 0\nTurbiedad | NTU | 2')
                    parametros = []
                    for linea in lineas.splitlines():
                        if linea.strip():
                            partes = [x.strip() for x in linea.split('|')]
                            if len(partes)>3:
                                parametros.append({'nombre':'','unidad':'','decimales':'invalid'})
                            else:
                                parametros.append({'nombre':partes[0],
                                                   'unidad':partes[1] if len(partes)>1 else '',
                                                   'decimales':partes[2] if len(partes)>2 and partes[2] else 2})
                    materiales.append({'nombre':nombre,'codigo_muestra':muestra,'descripcion':mdesc,
                                       'fecha_apertura':mi,'fecha_cierre':mf,'parametros':parametros})
            guardar = st.form_submit_button('💾 Guardar campaña en borrador',type='primary')
        x,y = st.columns(2)
        if x.button('➕ Agregar material',use_container_width=True):
            st.session_state.pa_nmateriales += 1
            st.rerun()
        if y.button('➖ Quitar último material',disabled=st.session_state.pa_nmateriales<=1,use_container_width=True):
            st.session_state.pa_nmateriales -= 1
            st.rerun()
        if guardar:
            try:
                datos = {'codigo':codigo,'titulo':titulo,'descripcion':descripcion,
                         'fecha_apertura':fecha(apertura_d,apertura_h),
                         'fecha_cierre':fecha(cierre_d,cierre_h),'materiales':materiales}
                nuevo_id = crear_campana_borrador(datos)
                st.success(f'Campaña creada correctamente. ID {nuevo_id}; estado borrador.')
                st.caption('Actualiza la página para verla en el listado.')
            except Exception as exc:
                st.error(f'No se pudo guardar: {exc}')
with t2:
    st.info('Próxima etapa: aceptación de condiciones, resultados duplicados y envíos definitivos.')
with t3:
    st.info('Próxima etapa: mediana, desviación estándar, z-score y dashboard.')
with t4:
    st.info('Próxima etapa: informes PDF por material y campaña.')
st.divider()
st.caption('PROVICHECK · Pruebas de Aptitud · Fase 2B')
pie_pagina()
