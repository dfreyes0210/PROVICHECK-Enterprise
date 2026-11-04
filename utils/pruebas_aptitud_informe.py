"""PROVICHECK | Informe PDF estadístico preliminar de Pruebas de Aptitud.
No modifica la base de datos. Genera bytes PDF a partir de una evaluación ya calculada.
"""
from __future__ import annotations
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, Circle, String

VERDE = colors.HexColor('#137545')
GRIS = colors.HexColor('#526176')
ROJO = colors.HexColor('#B83B3B')


def _numero(v, dec=2):
    return 'No disponible' if v is None else f'{float(v):.{dec}f}'


def _grafico_z(filas):
    puntos = [f for f in filas if f.get('z_score') is not None]
    if not puntos:
        return None
    ancho, alto = 490, 220
    izq, der, abajo, arriba = 55, 25, 42, 18
    zs = [float(f['z_score']) for f in puntos]
    minimo, maximo = min(-3.5, min(zs)-0.5), max(3.5, max(zs)+0.5)
    def y(z):
        return abajo + (z-minimo)/(maximo-minimo)*(alto-abajo-arriba)
    def x(i):
        return izq + (i+0.5)*(ancho-izq-der)/len(puntos)
    d = Drawing(ancho, alto)
    for z, color in [(-3, ROJO), (-2, colors.HexColor('#BD8B2E')), (0, GRIS), (2, colors.HexColor('#BD8B2E')), (3, ROJO)]:
        d.add(Line(izq, y(z), ancho-der, y(z), strokeColor=color, strokeWidth=0.8, strokeDashArray=[3,3] if z else None))
        d.add(String(izq-9, y(z)-3, f'{z:+d}', fontSize=8, textAnchor='end', fillColor=GRIS))
    for i, f in enumerate(puntos):
        z = float(f['z_score'])
        color = VERDE if abs(z)<=2 else (colors.HexColor('#D49A1A') if abs(z)<3 else ROJO)
        d.add(Circle(x(i), y(z), 4.8, fillColor=color, strokeColor=colors.white, strokeWidth=0.7))
        d.add(String(x(i), 20, str(f['id_usuario'])[:14], fontSize=7, textAnchor='middle', fillColor=GRIS))
    return d


def generar_informe_pdf(reporte: dict, simulacion: bool = False) -> bytes:
    """Devuelve el PDF en memoria; no publica ni persiste resultados."""
    memoria = BytesIO()
    doc = SimpleDocTemplate(memoria, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name='TituloPA', parent=estilos['Title'], fontSize=17, leading=21, textColor=VERDE, spaceAfter=8))
    estilos.add(ParagraphStyle(name='SubPA', parent=estilos['Heading2'], fontSize=11, textColor=VERDE, spaceBefore=12, spaceAfter=7))
    estilos.add(ParagraphStyle(name='PeqPA', parent=estilos['Normal'], fontSize=8, leading=12))
    estilos.add(ParagraphStyle(name='AvisoPA', parent=estilos['Normal'], fontSize=10, leading=14, textColor=ROJO, alignment=TA_CENTER, spaceAfter=9))
    elems = [Paragraph('PROVICHECK | Informe de Pruebas de Aptitud', estilos['TituloPA'])]
    if simulacion:
        elems.append(Paragraph('SIMULACIÓN — DATOS FICTICIOS — NO VÁLIDO COMO INFORME OFICIAL', estilos['AvisoPA']))
    else:
        elems.append(Paragraph('INFORME PRELIMINAR — REQUIERE REVISIÓN Y APROBACIÓN', estilos['AvisoPA']))
    fecha = datetime.now(ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M')
    info = [
        ['Fecha de generación', fecha],
        ['Material', str(reporte.get('material',''))],
        ['Parámetro', f"{reporte.get('parametro','')} ({reporte.get('unidad') or 'sin unidad'})"],
        ['Participantes con duplicados', str(reporte.get('participantes_con_duplicados_completos',0))],
        ['Valor asignado (mediana)', _numero(reporte.get('valor_asignado_mediana'))],
        ['Desviación observada (muestral)', _numero(reporte.get('desviacion_observada_muestral'))],
        ['Desviación de evaluación (σpt)', _numero(reporte.get('desviacion_evaluacion'))],
    ]
    t = Table(info, colWidths=[75*mm, 95*mm], hAlign='LEFT')
    t.setStyle(TableStyle([('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),
                           ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),
                           ('LINEBELOW',(0,0),(-1,-1),0.3,colors.HexColor('#DEE4E8'))]))
    elems += [t, Paragraph('Metodología de evaluación', estilos['SubPA']),
              Paragraph('Cada participante aporta el promedio de dos determinaciones completas. El valor asignado se calcula como la mediana de los promedios. Cuando se proporciona una desviación estándar de evaluación (σpt), se calcula z = (promedio del participante − valor asignado) / σpt. Criterios provisionales: |z| ≤ 2 satisfactorio; 2 &lt; |z| &lt; 3 cuestionable; |z| ≥ 3 no satisfactorio.', estilos['PeqPA']),
              Paragraph('Resultados individuales', estilos['SubPA'])]
    encabezados = ['Participante', 'Resultado 1', 'Resultado 2', 'Promedio', 'z', 'Clasificación']
    datos = [encabezados]
    for f in reporte.get('resultados',[]):
        datos.append([str(f.get('id_usuario',''))[:20], _numero(f.get('resultado_1')),
                      _numero(f.get('resultado_2')), _numero(f.get('promedio')),
                      _numero(f.get('z_score')), str(f.get('clasificacion','Sin evaluar'))])
    if len(datos)==1:
        datos.append(['Sin resultados','','','','',''])
    tabla = Table(datos, colWidths=[30*mm, 26*mm, 26*mm, 25*mm, 16*mm, 47*mm], repeatRows=1, hAlign='LEFT')
    tabla.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),VERDE),('TEXTCOLOR',(0,0),(-1,0),colors.white),
                               ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.5),
                               ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F2F6F7')]),
                               ('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#DCE4E7')),
                               ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),7),
                               ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elems.append(tabla)
    grafico = _grafico_z(reporte.get('resultados',[]))
    if grafico:
        elems.extend([Paragraph('Puntuaciones z por participante', estilos['SubPA']),grafico,
                      Paragraph('Cada punto representa un participante independiente. Líneas horizontales: z = 0, ±2 y ±3.', estilos['PeqPA'])])
    elems.extend([Paragraph('Observaciones y alcance', estilos['SubPA']),
                  Paragraph('La desviación estándar observada describe la dispersión del grupo y no sustituye a σpt. Los resultados deben revisarse conforme al procedimiento estadístico aprobado, la suficiencia de participantes y las reglas de confidencialidad. Este documento no constituye por sí mismo una autorización de competencia.', estilos['PeqPA'])])
    if reporte.get('participantes_con_duplicados_completos',0)<3:
        elems.append(Paragraph('Advertencia: menos de tres participantes con duplicados completos; la caracterización grupal es preliminar.', estilos['AvisoPA']))
    doc.build(elems)
    return memoria.getvalue()
