"""PROVICHECK | Informe PDF estadístico de comparaciones interanalistas.
No modifica Supabase. Conserva generar_informe_pdf(reporte, simulacion=False).
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

VERDE = colors.HexColor('#137545')
GRIS = colors.HexColor('#526176')
ROJO = colors.HexColor('#B83B3B')
AMARILLO = colors.HexColor('#BD8B2E')


def _numero(valor, dec=2):
    if valor is None:
        return 'No disponible'
    try:
        return f'{float(valor):.{dec}f}'
    except (ValueError, TypeError, OverflowError):
        return 'No disponible'


def _texto(valor):
    return escape(str(valor if valor is not None else ''))


def _grafico_z(filas):
    puntos = [f for f in filas if f.get('z_score') is not None]
    if not puntos:
        return None
    ancho, alto = 490, 220
    izq, der, abajo, arriba = 55, 25, 42, 18
    zs = [float(f['z_score']) for f in puntos]
    minimo = min(-3.5, min(zs) - 0.5)
    maximo = max(3.5, max(zs) + 0.5)

    def y(z):
        return abajo + (z - minimo) / (maximo - minimo) * (alto - abajo - arriba)

    def x(i):
        return izq + (i + 0.5) * (ancho - izq - der) / len(puntos)

    dibujo = Drawing(ancho, alto)
    for z, color in [(-3, ROJO), (-2, AMARILLO), (0, GRIS), (2, AMARILLO), (3, ROJO)]:
        dibujo.add(Line(izq, y(z), ancho - der, y(z), strokeColor=color,
                         strokeWidth=0.8, strokeDashArray=[3, 3] if z else None))
        dibujo.add(String(izq - 9, y(z) - 3, f'{z:+d}', fontSize=8,
                           textAnchor='end', fillColor=GRIS))
    for i, fila in enumerate(puntos):
        z = float(fila['z_score'])
        color = VERDE if abs(z) <= 2 else (AMARILLO if abs(z) < 3 else ROJO)
        dibujo.add(Circle(x(i), y(z), 4.8, fillColor=color,
                          strokeColor=colors.white, strokeWidth=0.7))
        dibujo.add(String(x(i), 20, str(fila.get('id_usuario', ''))[:14],
                           fontSize=7, textAnchor='middle', fillColor=GRIS))
    return dibujo


def generar_informe_pdf(reporte: dict, simulacion: bool = False) -> bytes:
    """Genera un PDF en memoria, sin modificar ni publicar resultados."""
    memoria = BytesIO()
    doc = SimpleDocTemplate(
        memoria, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm,
    )
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name='TituloPA', parent=estilos['Title'],
                               fontSize=17, leading=21, textColor=VERDE, spaceAfter=8))
    estilos.add(ParagraphStyle(name='SubPA', parent=estilos['Heading2'],
                               fontSize=11, textColor=VERDE, spaceBefore=12, spaceAfter=7))
    estilos.add(ParagraphStyle(name='PeqPA', parent=estilos['Normal'],
                               fontSize=8, leading=12))
    estilos.add(ParagraphStyle(name='AvisoPA', parent=estilos['Normal'],
                               fontSize=10, leading=14, textColor=ROJO,
                               alignment=TA_CENTER, spaceAfter=9))

    elems = [Paragraph('PROVICHECK | Informe de Pruebas de Aptitud', estilos['TituloPA'])]
    if simulacion:
        elems.append(Paragraph(
            'SIMULACIÓN — DATOS FICTICIOS — NO VÁLIDO COMO INFORME OFICIAL',
            estilos['AvisoPA']))
    else:
        elems.append(Paragraph(
            'INFORME PRELIMINAR — REQUIERE REVISIÓN Y APROBACIÓN',
            estilos['AvisoPA']))

    fecha = datetime.now(ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M')
    filas = reporte.get('resultados') or []
    completos = int(reporte.get('participantes_con_duplicados_completos') or 0)
    numero_individuales = reporte.get('numero_resultados_individuales')
    desviacion_principal = reporte.get(
        'desviacion_resultados_individuales',
        reporte.get('desviacion_observada_muestral'))
    desviacion_promedios = reporte.get('desviacion_promedios_participantes')
    sigma = reporte.get('desviacion_evaluacion')

    info = [
        ['Fecha de generación', fecha],
        ['Material', _texto(reporte.get('material'))],
        ['Parámetro', f"{_texto(reporte.get('parametro'))} ({_texto(reporte.get('unidad') or 'sin unidad')})"],
        ['Participantes con duplicados', str(completos)],
        ['Resultados individuales válidos', str(numero_individuales) if numero_individuales is not None else 'No disponible'],
        ['Valor asignado (mediana)', _numero(reporte.get('valor_asignado_mediana'))],
        ['Desv. principal (resultados individuales)', _numero(desviacion_principal)],
        ['Desv. secundaria (promedios)', _numero(desviacion_promedios)],
        ['Desviación de evaluación (σpt)', _numero(sigma)],
    ]
    tabla_info = Table(info, colWidths=[84 * mm, 86 * mm], hAlign='LEFT')
    tabla_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#DEE4E8')),
    ]))
    elems.append(tabla_info)

    elems.append(Paragraph('Metodología de evaluación', estilos['SubPA']))
    elems.append(Paragraph(
        'La dispersión principal es la desviación estándar muestral de todos los '
        'resultados individuales válidos; incluye los duplicados y no equivale a '
        'una desviación entre participantes independientes. La dispersión secundaria '
        'es la desviación estándar muestral de los promedios de participantes con '
        'dos resultados completos. El valor asignado es la mediana de esos promedios. '
        'Cuando se define σpt, se calcula z = (promedio del participante − valor '
        'asignado) / σpt. Criterios provisionales: |z| ≤ 2 satisfactorio; '
        '2 &lt; |z| &lt; 3 cuestionable; |z| ≥ 3 no satisfactorio.',
        estilos['PeqPA']))

    elems.append(Paragraph('Resultados individuales', estilos['SubPA']))
    datos = [['Participante', 'Resultado 1', 'Resultado 2', 'Promedio', 'z', 'Clasificación']]
    for fila in filas:
        datos.append([
            _texto(fila.get('id_usuario'))[:20],
            _numero(fila.get('resultado_1')),
            _numero(fila.get('resultado_2')),
            _numero(fila.get('promedio')),
            _numero(fila.get('z_score')),
            _texto(fila.get('clasificacion') or 'Sin evaluar'),
        ])
    if len(datos) == 1:
        datos.append(['Sin resultados', '', '', '', '', ''])

    tabla = Table(datos, colWidths=[30 * mm, 26 * mm, 26 * mm, 25 * mm, 16 * mm, 47 * mm],
                  repeatRows=1, hAlign='LEFT')
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VERDE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F6F7')]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#DCE4E7')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    elems.append(tabla)

    conteos = Counter(f.get('clasificacion') for f in filas)
    elems.append(Paragraph('Resumen de evaluación', estilos['SubPA']))
    if sigma is None:
        elems.append(Paragraph(
            'No se calcularon puntuaciones z ni categorías de desempeño porque '
            'no se proporcionó una desviación estándar de evaluación (σpt).',
            estilos['PeqPA']))
    else:
        evaluados = sum(conteos.get(c, 0) for c in
                        ('Satisfactorio', 'Cuestionable', 'No satisfactorio'))
        resumen = []
        for categoria in ('Satisfactorio', 'Cuestionable', 'No satisfactorio'):
            cantidad = conteos.get(categoria, 0)
            porcentaje = 100 * cantidad / evaluados if evaluados else 0
            resumen.append(f'{categoria}: {cantidad} ({porcentaje:.1f} %)')
        elems.append(Paragraph(' | '.join(resumen), estilos['PeqPA']))
        if conteos.get('Cuestionable', 0) or conteos.get('No satisfactorio', 0):
            elems.append(Paragraph(
                'Los resultados cuestionables o no satisfactorios requieren '
                'revisión técnica antes de adoptar decisiones sobre competencia.',
                estilos['PeqPA']))

    grafico = _grafico_z(filas)
    if grafico is not None:
        elems.append(Paragraph('Puntuaciones z por participante', estilos['SubPA']))
        elems.append(grafico)
        elems.append(Paragraph(
            'Cada punto representa el promedio de los duplicados de un participante. '
            'Líneas horizontales: z = 0, ±2 y ±3.', estilos['PeqPA']))

    # Condiciones documentadas para la primera campaña de tres calidades de azúcar.
    # Se incluyen como descripción del procedimiento previsto, sujeto a confirmación
    # del responsable antes de aprobar el informe; no se infieren desde Supabase.
    elems.append(Paragraph(
        'Preparación de muestras, condiciones del ejercicio y alcance',
        estilos['SubPA']))
    elems.append(Paragraph(
        '<b>Preparación y fraccionamiento.</b> Para la campaña inicial de comparación '
        'interanalistas de tres calidades de azúcar, se ha previsto disponer de '
        'aproximadamente 5 kg de muestra por calidad. Cada muestra se somete a '
        'pasos sucesivos por un cuarteador para favorecer su homogeneización y '
        'se fracciona en porciones de aproximadamente 500 g, envasadas en bolsas '
        'de polipropileno selladas. Esta descripción corresponde al procedimiento '
        'de preparación informado para la campaña y debe ser confirmada por el '
        'responsable antes de aprobar el documento.', estilos['PeqPA']))
    elems.append(Paragraph(
        '<b>Conservación y distribución.</b> Las porciones se conservan '
        'aproximadamente 10 días en una oficina bajo condiciones ambientales '
        'controladas y se distribuyen simultáneamente a los participantes. '
        'Los ensayos se ejecutan durante los turnos habituales de trabajo, '
        'dentro de un plazo máximo de 72 horas, aplicando los métodos '
        'establecidos y registrando las dos determinaciones por parámetro.',
        estilos['PeqPA']))
    elems.append(Paragraph(
        '<b>Homogeneidad y estabilidad.</b> El cuarteo, el sellado, la conservación '
        'y la distribución coordinada son medidas para reducir fuentes de '
        'variación del material. No constituyen, por sí solas, demostración '
        'experimental de homogeneidad o estabilidad. No se realizaron ni se '
        'presuponen estudios específicos para demostrar estas propiedades; '
        'su posible influencia debe considerarse al interpretar los resultados.',
        estilos['PeqPA']))
    elems.append(Paragraph(
        '<b>Competencia y autorización.</b> La comparación interanalistas '
        'proporciona evidencia objetiva del desempeño técnico que puede '
        'utilizarse, junto con otras evidencias de competencia, para sustentar '
        'la decisión del líder del laboratorio sobre la autorización de '
        'personal para realizar ensayos, en el marco de la ISO/IEC 17025:2017. '
        'Un resultado satisfactorio no equivale a una autorización automática: '
        'la decisión requiere evaluación documentada por la persona facultada.',
        estilos['PeqPA']))
    elems.append(Paragraph(
        '<b>Alcance.</b> Se trata de una comparación interna de desempeño '
        'interanalistas, no de un programa acreditado de ensayos de aptitud. '
        'Las condiciones descritas deben verificarse para esta campaña y no '
        'deben trasladarse automáticamente a campañas posteriores.',
        estilos['PeqPA']))

    elems.append(Paragraph('Observaciones y alcance', estilos['SubPA']))
    elems.append(Paragraph(
        'Las desviaciones observadas describen la dispersión de los datos y no '
        'sustituyen automáticamente a σpt. Antes de utilizar la evaluación para '
        'decisiones oficiales deben documentarse el origen de σpt, la suficiencia '
        'del grupo y las condiciones de preparación, homogeneidad y estabilidad '
        'del material. Este documento no constituye por sí mismo una autorización '
        'formal de competencia.', estilos['PeqPA']))
    if completos < 3:
        elems.append(Paragraph(
            'Advertencia: menos de tres participantes con duplicados completos; '
            'la caracterización grupal es preliminar.', estilos['AvisoPA']))

    doc.build(elems)
    return memoria.getvalue()
