"""PROVICHECK | Pruebas de Aptitud. Fase 3A: publicación controlada."""
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.pruebas_aptitud_estadistica import evaluar_parametro, evaluar_simulacion_color
from utils.ui import aplicar_estilo, encabezado, pie_pagina, requerir_autenticacion, sidebar_pro
from utils.pruebas_aptitud_db import (
    listar_campanas, listar_materiales, listar_parametros,
    crear_campana_borrador, publicar_campana,
    consultar_mi_participacion, registrar_mi_participacion,
    listar_parametros_registro, consultar_mi_borrador, guardar_mi_borrador,
    enviar_mis_resultados_definitivos,
)

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
st.info('Módulo de comparación interanalistas. Las evaluaciones definitivas requieren criterios estadísticos aprobados y pruebas integrales previas a producción.')

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
                if gestor and camp['estado'] == 'borrador':
                    st.divider()
                    st.warning('Publicar permite que los analistas vean esta campaña. Esta acción no se revierte desde esta pantalla.')
                    confirmar = st.checkbox('Confirmo que revisé materiales, parámetros y fechas', key=f"pa_confirma_{camp['id']}")
                    if st.button('📢 Publicar campaña', key=f"pa_publicar_{camp['id']}", disabled=not confirmar, type='primary'):
                        try:
                            publicar_campana(camp['id'])
                            st.success('Campaña publicada correctamente y registrada en auditoría.')
                            st.rerun()
                        except Exception as exc:
                            st.error(f'No se pudo publicar: {exc}')
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
    st.subheader('Participación en campañas publicadas')
    st.caption('La declaración se registra una sola vez por campaña y no puede editarse desde esta pantalla.')
    st.info('Puedes guardar borradores y enviar definitivamente los resultados por material. Después del envío no podrás modificarlos.')
    try:
        publicadas = [c for c in listar_campanas() if c['estado'] == 'publicada']
        if not publicadas:
            st.info('No hay campañas publicadas disponibles.')
        for camp in publicadas:
            with st.container(border=True):
                st.markdown(f"**{camp['codigo']} · {camp['titulo']}**")
                st.caption(f"Apertura: {mostrar_fecha(camp['fecha_apertura'])} | Cierre: {mostrar_fecha(camp['fecha_cierre'])}")
                registro = consultar_mi_participacion(camp['id'])
                if registro:
                    st.success('Tu aceptación y declaración ya quedaron registradas.')
                    if registro.get('conflicto_interes'):
                        st.warning('Declaraste un conflicto de interés. Tu participación queda bloqueada para el registro de resultados hasta que exista una revisión formal.')
                    else:
                        st.caption('Sin conflicto de interés declarado. Puedes registrar borradores durante las fechas habilitadas.')
                else:
                    ahora = datetime.now(ZONA)
                    apertura = datetime.fromisoformat(camp['fecha_apertura'].replace('Z', '+00:00'))
                    cierre = datetime.fromisoformat(camp['fecha_cierre'].replace('Z', '+00:00'))
                    if not (apertura <= ahora <= cierre):
                        st.warning('La campaña no está dentro del periodo habilitado para participar.')
                    else:
                        with st.form(f"pa_participacion_{camp['id']}"):
                            st.markdown('**Condiciones de participación**')
                            st.write('Me comprometo a analizar las muestras de manera independiente, mantener la confidencialidad de los resultados, seguir los métodos vigentes y reportar cualquier situación que comprometa mi imparcialidad.')
                            acepto = st.checkbox('He leído y acepto las condiciones de participación.')
                            conflicto = st.radio('¿Existe algún conflicto de interés o impedimento?', ['Selecciona una respuesta', 'No', 'Sí'], horizontal=True)
                            detalle = st.text_area('Describe el conflicto o impedimento (obligatorio si respondes Sí)', max_chars=2000)
                            enviar = st.form_submit_button('Registrar aceptación y declaración', type='primary')
                        if enviar:
                            try:
                                if conflicto == 'Selecciona una respuesta':
                                    raise ValueError('Selecciona Sí o No en la declaración de conflicto de interés.')
                                registrar_mi_participacion(camp['id'], acepto, conflicto == 'Sí', detalle)
                                st.success('Participación registrada correctamente.')
                                st.rerun()
                            except Exception as exc:
                                st.error(f'No fue posible registrar tu participación: {exc}')
    except Exception as exc:
        st.error(f'No fue posible consultar las participaciones: {exc}')

    st.divider()
    st.subheader('Resultados por material')
    st.caption('Guarda los duplicados en borrador antes de enviarlos definitivamente. Los campos vacíos se conservan como pendientes.')
    try:
        for camp in [c for c in listar_campanas() if c['estado'] == 'publicada']:
            participacion = consultar_mi_participacion(camp['id'])
            if not participacion or not participacion.get('condiciones_aceptadas'):
                continue
            if participacion.get('conflicto_interes'):
                st.warning(f"{camp['codigo']}: participación bloqueada por conflicto declarado.")
                continue
            ahora = datetime.now(ZONA)
            inicio_c = datetime.fromisoformat(camp['fecha_apertura'].replace('Z', '+00:00'))
            fin_c = datetime.fromisoformat(camp['fecha_cierre'].replace('Z', '+00:00'))
            for mat in listar_materiales(camp['id']):
                mid = mat['id']
                with st.container(border=True):
                    st.markdown(f"**{camp['codigo']} · {mat['nombre']}**")
                    inicio_m = datetime.fromisoformat(mat['fecha_apertura'].replace('Z', '+00:00')) if mat.get('fecha_apertura') else inicio_c
                    fin_m = datetime.fromisoformat(mat['fecha_cierre'].replace('Z', '+00:00')) if mat.get('fecha_cierre') else fin_c
                    borrador = consultar_mi_borrador(mid)
                    if borrador and borrador.get('estado') == 'enviado':
                        st.success('Resultados enviados definitivamente. No se pueden modificar.')
                        st.caption(f"Entrega ID: {borrador['id']}")
                        continue
                    if not (max(inicio_c, inicio_m) <= ahora <= min(fin_c, fin_m)):
                        st.warning('El material está fuera de su plazo de registro.')
                        continue
                    previos = {int(r['parametro_id']): r for r in (borrador or {}).get('resultados', [])}
                    parametros = listar_parametros_registro(mid)
                    if not parametros:
                        st.warning('Este material no tiene parámetros activos.')
                        continue
                    with st.form(f'pa_borrador_{camp["id"]}_{mid}'):
                        filas = []
                        for par in parametros:
                            pid = int(par['id'])
                            anterior = previos.get(pid, {})
                            st.markdown(f"**{par['nombre']}** ({par.get('unidad') or 'sin unidad'})")
                            c1, c2 = st.columns(2)
                            r1 = c1.text_input('Resultado 1', value=str(anterior.get('resultado_1') if anterior.get('resultado_1') is not None else ''), key=f'pa_r1_{mid}_{pid}')
                            r2 = c2.text_input('Resultado 2', value=str(anterior.get('resultado_2') if anterior.get('resultado_2') is not None else ''), key=f'pa_r2_{mid}_{pid}')
                            obs = st.text_input('Observación', value=anterior.get('observacion') or '', key=f'pa_obs_{mid}_{pid}')
                            filas.append({'parametro_id': pid, 'resultado_1': r1, 'resultado_2': r2, 'observacion': obs})
                        guardar_borrador = st.form_submit_button('💾 Guardar borrador', type='primary')
                    if guardar_borrador:
                        try:
                            guardar_mi_borrador(camp['id'], mid, filas)
                            st.success('Borrador guardado correctamente.')
                            st.rerun()
                        except Exception as exc:
                            st.error(f'No se pudo guardar el borrador: {exc}')
                    if borrador and borrador.get('estado') == 'borrador':
                        st.divider()
                        st.markdown('**Envío definitivo del material**')
                        st.warning('Después de confirmar, los resultados quedarán bloqueados. Revisa los valores y guarda cualquier cambio en el borrador antes de enviarlo.')
                        resultados_guardados = {int(r['parametro_id']): r for r in borrador.get('resultados', [])}
                        incompletos = [par['nombre'] for par in parametros
                                       if (int(par['id']) not in resultados_guardados
                                           or resultados_guardados[int(par['id'])].get('resultado_1') is None
                                           or resultados_guardados[int(par['id'])].get('resultado_2') is None)]
                        if incompletos:
                            st.warning('Parámetros incompletos: ' + ', '.join(incompletos) + '. Para enviarlos así debes justificarlo.')
                        with st.form(f'pa_envio_{camp["id"]}_{mid}'):
                            observacion_envio = st.text_area(
                                'Observación general del envío' + (' *' if incompletos else ''),
                                max_chars=2000,
                                help='Obligatoria si existen parámetros sin los dos resultados.')
                            confirmar_envio = st.checkbox('Confirmo que revisé los resultados guardados y autorizo el envío definitivo sin posibilidad de edición.')
                            enviar_definitivo = st.form_submit_button('📤 Enviar resultados definitivamente', type='primary')
                        if enviar_definitivo:
                            try:
                                if not confirmar_envio:
                                    raise ValueError('Marca la casilla de confirmación antes de enviar.')
                                if incompletos and not observacion_envio.strip():
                                    raise ValueError('Debes justificar los resultados incompletos.')
                                entrega_id = enviar_mis_resultados_definitivos(
                                    camp['id'], mid, observacion_envio, confirmar_envio)
                                st.success(f'Resultados enviados definitivamente. Entrega ID: {entrega_id}.')
                                st.rerun()
                            except Exception as exc:
                                st.error(f'No se pudo realizar el envío definitivo: {exc}')
    except Exception as exc:
        st.error(f'No fue posible cargar los borradores: {exc}')
with t3:
    st.subheader('Evaluación estadística interanalistas')
    modo_simulado = st.toggle('🧪 Activar simulación de 5 participantes (sin guardar en Supabase)', value=False, key='pa5_modo_simulado')
    if modo_simulado:
        st.warning('MODO SIMULACIÓN · Datos ficticios SIM-001 a SIM-005. No son resultados reales, no se guardan en Supabase y no son válidos para autorizar analistas.')
    st.caption('Solo se incluyen entregas definitivas. Cada participante aporta el promedio de sus dos duplicados completos.')
    if not gestor:
        st.info('La evaluación consolidada está reservada al líder del Laboratorio de Fábrica y a los administradores. Los analistas no pueden consultar resultados de otros participantes.')
    else:
        try:
            campanas_eval = [{'id': -1, 'codigo': 'SIMULACION-5B', 'titulo': 'Color · 5 participantes ficticios', 'estado': 'simulación'}] if modo_simulado else listar_campanas()
            if not campanas_eval:
                st.info('No hay campañas registradas para evaluar.')
            else:
                opciones_c = {f"{c['codigo']} · {c['titulo']} ({c['estado']})": c for c in campanas_eval}
                etiqueta_c = st.selectbox('Campaña', list(opciones_c), key='pa5_campana')
                camp_eval = opciones_c[etiqueta_c]
                materiales_eval = [{'id': -1, 'nombre': 'AZÚCAR BLANCO (SIMULACIÓN)', 'codigo_muestra': 'DEMO'}] if modo_simulado else listar_materiales(camp_eval['id'])
                if not materiales_eval:
                    st.info('Esta campaña todavía no tiene materiales.')
                else:
                    opciones_m = {f"{m['nombre']} · {m.get('codigo_muestra') or 'Sin código'} [ID {m['id']}]": m for m in materiales_eval}
                    etiqueta_m = st.selectbox('Material', list(opciones_m), key='pa5_material')
                    mat_eval = opciones_m[etiqueta_m]
                    parametros_eval = [{'id': -1, 'nombre': 'Color', 'unidad': 'UI', 'decimales': 2}] if modo_simulado else listar_parametros_registro(mat_eval['id'])
                    if not parametros_eval:
                        st.warning('El material no tiene parámetros activos para evaluar.')
                    else:
                        opciones_p = {f"{p['nombre']} ({p.get('unidad') or 'sin unidad'}) [ID {p['id']}]": p for p in parametros_eval}
                        etiqueta_p = st.selectbox('Parámetro', list(opciones_p), key='pa5_parametro')
                        par_eval = opciones_p[etiqueta_p]
                        st.markdown('**Desviación estándar para evaluación (σpt)**')
                        st.caption('Debe proceder del procedimiento estadístico aprobado. No se sustituye automáticamente por la desviación observada de los participantes.')
                        usar_sigma = st.checkbox('Ingresar σpt para calcular puntuaciones z', value=False, key='pa5_usa_sigma')
                        if modo_simulado:
                            st.caption('Para comprobar las categorías puedes usar σpt = 5 UI SOLO en esta simulación. No es un valor aprobado del laboratorio.')
                        sigma_eval = None
                        if usar_sigma:
                            sigma_eval = st.number_input('σpt (valor positivo, en la unidad del parámetro)', min_value=0.000000001, value=5.0 if modo_simulado else 1.0, format='%.8f', key=f"pa5_sigma_{par_eval['id']}")
                            st.warning('La σpt ingresada es temporal: no se guarda en Supabase ni constituye un criterio aprobado por sí sola.')
                        if st.button('📊 Generar evaluación', type='primary', key='pa5_generar'):
                            try:
                                st.session_state['pa5_reporte'] = (
                                    evaluar_simulacion_color(sigma_eval) if modo_simulado else
                                    evaluar_parametro(camp_eval['id'], mat_eval['id'], par_eval['id'], sigma_eval)
                                )
                                st.session_state['pa5_seleccion'] = (modo_simulado, camp_eval['id'], mat_eval['id'], par_eval['id'], sigma_eval)
                            except Exception as exc:
                                st.session_state.pop('pa5_reporte', None)
                                st.error(f'No fue posible generar la evaluación: {exc}')
                        seleccion_actual = (modo_simulado, camp_eval['id'], mat_eval['id'], par_eval['id'], sigma_eval)
                        reporte = st.session_state.get('pa5_reporte') if st.session_state.get('pa5_seleccion') == seleccion_actual else None
                        if reporte is not None:
                            if modo_simulado:
                                st.error('RESULTADOS SIMULADOS — PROHIBIDO USO EN INFORMES OFICIALES')
                            dec = max(0, min(int(reporte.get('decimales') or 2), 8))
                            def fmt_num(x):
                                return '—' if x is None else f'{x:,.{dec}f}'
                            resultados = reporte['resultados']
                            validos = [r for r in resultados if r['promedio'] is not None]
                            a, b, c, d = st.columns(4)
                            a.metric('Entregas con resultado', reporte['participantes_con_resultados'])
                            b.metric('Duplicados completos', reporte['participantes_con_duplicados_completos'])
                            c.metric('Valor asignado · mediana', fmt_num(reporte['valor_asignado_mediana']))
                            d.metric('Resultados individuales válidos', reporte.get('numero_resultados_individuales', '—'))
                            st.markdown('#### Dispersión de los resultados')
                            disp1, disp2, disp3 = st.columns(3)
                            disp1.metric('Desv. observada principal · resultados individuales', fmt_num(reporte.get('desviacion_resultados_individuales', reporte.get('desviacion_observada_muestral'))))
                            disp2.metric('Desv. secundaria · promedios por analista', fmt_num(reporte.get('desviacion_promedios_participantes')))
                            disp3.metric('σpt · desviación para evaluación', fmt_num(reporte.get('desviacion_evaluacion')))
                            st.caption('Las dos desviaciones observadas son muestrales y descriptivas. La principal incluye todos los resultados individuales válidos, incluso si falta su duplicado; la secundaria incluye solo promedios de duplicados completos. El z-score se calcula con el promedio del participante y una σpt independiente, que debe justificarse documentalmente.')
                            if len(validos) < 3:
                                st.warning('Evaluación preliminar: hay menos de tres participantes con duplicados completos. No es suficiente para caracterizar de manera robusta el grupo; no se debe emitir una conclusión definitiva.')
                            if reporte['desviacion_evaluacion'] is None:
                                st.info('No se han calculado z-scores ni categorías porque todavía no se ha definido σpt.')
                            st.markdown('#### Resultados individuales')
                            if not resultados:
                                st.info('Todavía no existen resultados enviados para este parámetro.')
                            else:
                                tabla = pd.DataFrame([{
                                    'Participante': r['id_usuario'],
                                    'Resultado 1': r['resultado_1'],
                                    'Resultado 2': r['resultado_2'],
                                    'Promedio': r['promedio'],
                                    'z-score': r['z_score'],
                                    'Clasificación': r['clasificacion'],
                                } for r in resultados])
                                st.dataframe(tabla, hide_index=True, use_container_width=True)
                                st.download_button('⬇️ Exportar resultados (CSV)', data=tabla.to_csv(index=False).encode('utf-8-sig'),
                                                   file_name=("SIMULACION_NO_OFICIAL_COLOR_5B.csv" if modo_simulado else f"PA_{camp_eval['codigo']}_material_{mat_eval['id']}_parametro_{par_eval['id']}.csv"),
                                                   mime='text/csv', key='pa5_descarga_csv')
                            if validos:
                                st.markdown('#### Comparación de resultados promedio')
                                graf = go.Figure()
                                graf.add_trace(go.Scatter(x=[r['id_usuario'] for r in validos],
                                                          y=[r['promedio'] for r in validos],
                                                          mode='markers', name='Promedio por participante',
                                                          marker=dict(size=11)))
                                asignado = reporte['valor_asignado_mediana']
                                graf.add_hline(y=asignado, line_dash='dash', annotation_text='Mediana del grupo')
                                sigma = reporte['desviacion_evaluacion']
                                if sigma is not None:
                                    graf.add_hline(y=asignado + 2*sigma, line_dash='dot', annotation_text='+2 σpt')
                                    graf.add_hline(y=asignado - 2*sigma, line_dash='dot', annotation_text='−2 σpt')
                                    graf.add_hline(y=asignado + 3*sigma, line_dash='dashdot', annotation_text='+3 σpt')
                                    graf.add_hline(y=asignado - 3*sigma, line_dash='dashdot', annotation_text='−3 σpt')
                                graf.update_layout(xaxis_title='Participante (ID)',
                                                   yaxis_title=f"{reporte['parametro']} ({reporte['unidad'] or 'sin unidad'})",
                                                   height=430, margin=dict(l=20,r=20,t=25,b=25))
                                st.plotly_chart(graf, use_container_width=True)
                                if sigma is not None:
                                    st.markdown('#### Gráfica individual de puntuaciones z')
                                    st.caption('Cada punto corresponde a un participante independiente. Las líneas horizontales representan los criterios provisionales de evaluación.')
                                    fig_z = go.Figure()
                                    colores_z = {
                                        'Satisfactorio': '#16824A',
                                        'Cuestionable': '#E3A008',
                                        'No satisfactorio': '#D64545',
                                    }
                                    for categoria, color in colores_z.items():
                                        puntos = [r for r in validos if r['clasificacion'] == categoria and r['z_score'] is not None]
                                        if puntos:
                                            fig_z.add_trace(go.Scatter(
                                                x=[r['id_usuario'] for r in puntos],
                                                y=[r['z_score'] for r in puntos],
                                                mode='markers', name=categoria,
                                                marker=dict(size=14, color=color, line=dict(color='white', width=1)),
                                                customdata=[r['promedio'] for r in puntos],
                                                hovertemplate='Participante: %{x}<br>z = %{y:.2f}<br>Promedio = %{customdata:.3f}<extra></extra>',
                                            ))
                                    fig_z.add_hline(y=0, line_dash='solid', line_color='#65748B', annotation_text='z = 0')
                                    for limite, estilo in [(2, 'dot'), (-2, 'dot'), (3, 'dash'), (-3, 'dash')]:
                                        fig_z.add_hline(y=limite, line_dash=estilo, line_color='#9A6D25' if abs(limite)==2 else '#B34B4B', annotation_text=f'z = {limite:+d}')
                                    fig_z.update_layout(
                                        xaxis_title='Participante (ID)', yaxis_title='Puntuación z',
                                        height=430, margin=dict(l=25, r=35, t=25, b=30),
                                        legend_title='Clasificación',
                                    )
                                    fig_z.update_xaxes(type='category', categoryorder='array',
                                                       categoryarray=[r['id_usuario'] for r in validos])
                                    st.plotly_chart(fig_z, use_container_width=True)
                                    st.markdown('#### Distribución de clasificaciones')
                                    conteos = pd.Series([r['clasificacion'] for r in validos]).value_counts()
                                    fig_cat = go.Figure(go.Bar(x=list(conteos.index), y=list(conteos.values),
                                                               text=list(conteos.values), textposition='auto'))
                                    fig_cat.update_layout(yaxis_title='Participantes', height=320,
                                                          margin=dict(l=20,r=20,t=20,b=20))
                                    st.plotly_chart(fig_cat, use_container_width=True)
                                    st.caption('Criterio provisional: |z| ≤ 2 satisfactorio; 2 < |z| < 3 cuestionable; |z| ≥ 3 no satisfactorio. Validar contra el procedimiento vigente antes de emitir informes oficiales.')
                        else:
                            st.caption('Selecciona campaña, material y parámetro; luego pulsa «Generar evaluación».')
        except Exception as exc:
            st.error(f'No fue posible cargar el dashboard estadístico: {exc}')
with t4:
    st.subheader('Informe estadístico de pruebas de aptitud')
    if not gestor:
        st.info('Solo el líder autorizado y los administradores pueden generar informes consolidados.')
    else:
        reporte_pdf = st.session_state.get('pa5_reporte')
        seleccion_pdf = st.session_state.get('pa5_seleccion')
        if reporte_pdf is None or seleccion_pdf is None:
            st.info('Primero genera una evaluación en la pestaña «Evaluación y dashboard». Luego regresa aquí para obtener el PDF.')
        else:
            es_simulacion = bool(seleccion_pdf[0])
            if es_simulacion:
                st.warning('INFORME DE SIMULACIÓN · Datos ficticios. No válido para decisiones sobre analistas.')
            else:
                st.warning('Informe preliminar. Verifica el procedimiento, la desviación de evaluación y la suficiencia del grupo antes de usarlo oficialmente.')
            st.write(f"**Material:** {reporte_pdf['material']}  |  **Parámetro:** {reporte_pdf['parametro']}")
            if st.button('📄 Preparar informe PDF', type='primary', key='pa5_preparar_pdf'):
                try:
                    from utils.pruebas_aptitud_informe import generar_informe_pdf
                    st.session_state['pa5_pdf'] = generar_informe_pdf(reporte_pdf, es_simulacion)
                    st.session_state['pa5_pdf_origen'] = seleccion_pdf
                except Exception as exc:
                    st.session_state.pop('pa5_pdf', None)
                    st.error(f'No fue posible preparar el PDF: {exc}')
            if st.session_state.get('pa5_pdf_origen') == seleccion_pdf and st.session_state.get('pa5_pdf'):
                st.download_button('⬇️ Descargar informe PDF', data=st.session_state['pa5_pdf'],
                                   file_name='PROVICHECK_Pruebas_Aptitud_SIMULACION.pdf' if es_simulacion else 'PROVICHECK_Pruebas_Aptitud_PRELIMINAR.pdf',
                                   mime='application/pdf', key='pa5_descargar_pdf')
st.divider()
st.caption('PROVICHECK · Pruebas de Aptitud · Comparaciones interanalistas')
pie_pagina()
