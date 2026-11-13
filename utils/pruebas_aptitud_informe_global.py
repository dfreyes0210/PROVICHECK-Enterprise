
"""PROVICHECK: informe global preliminar de una campaña de aptitud.

Generador puro: NO consulta ni modifica Supabase. Recibe datos previamente
validados y anonimizados por una capa de acceso restringida al gestor.
No sustituye el informe individual existente.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
from math import isfinite
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN = colors.HexColor('#116B48')
GREY = colors.HexColor('#596575')


def _safe(value):
    return escape(str(value if value is not None else ''))


def _fmt(value, digits=3):
    try:
        return f'{float(value):.{max(0, min(int(digits), 6))}f}' if value is not None else '—'
    except (TypeError, ValueError, OverflowError):
        return '—'


def _table(rows, widths, header=True):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#DAE2E6')),
    ]
    if header:
        styles.extend([
            ('BACKGROUND', (0, 0), (-1, 0), GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F7F7')]),
        ])
    table.setStyle(TableStyle(styles))
    return table


def _number(value):
    try:
        number = float(value)
        return number if isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _evaluacion(fila, valor_asignado, sigma):
    """Recalcula z usando la sigma de la metodología seleccionada."""
    promedio = _number(fila.get('promedio'))
    if promedio is None:
        r1 = _number(fila.get('resultado_1'))
        r2 = _number(fila.get('resultado_2'))
        if r1 is not None and r2 is not None:
            promedio = (r1 + r2) / 2

    if promedio is None or valor_asignado is None or sigma is None or sigma <= 0:
        return promedio, None, 'Sin evaluar'

    z = (promedio - valor_asignado) / sigma
    categoria = (
        'Satisfactorio' if abs(z) <= 2 else
        'Cuestionable' if abs(z) < 3 else
        'No satisfactorio'
    )
    return promedio, z, categoria


def _grafica_resultados(filas, asignado, unidad):
    """Gráfica vectorial de duplicados, promedios y valor asignado."""
    datos = []
    for fila in filas:
        promedio = _number(fila.get('promedio'))
        r1 = _number(fila.get('resultado_1'))
        r2 = _number(fila.get('resultado_2'))
        if promedio is None and r1 is not None and r2 is not None:
            promedio = (r1 + r2) / 2
        datos.append((str(fila.get('codigo_anonimo', '')), r1, r2, promedio))

    valores = [
        v for _, a, b, c in datos
        for v in (a, b, c) if v is not None
    ]
    if asignado is not None:
        valores.append(asignado)
    if not valores:
        return None

    width, height = 480, 180
    d = Drawing(width, height)
    left, right, bottom, top = 49, 12, 34, 16
    ymin, ymax = min(valores), max(valores)
    pad = (ymax - ymin) * .13 if ymax > ymin else max(abs(ymin) * .01, .001)
    ymin, ymax = ymin - pad, ymax + pad

    def X(i):
        return left + (i + .5) * (width - left - right) / max(len(datos), 1)

    def Y(v):
        return bottom + (v - ymin) / (ymax - ymin) * (height - bottom - top)

    for j in range(5):
        v = ymin + j * (ymax - ymin) / 4
        y = Y(v)
        d.add(Line(
            left, y, width-right, y,
            strokeColor=colors.HexColor('#E1E8E9'), strokeWidth=.5
        ))
        d.add(String(
            left-5, y-2, f'{v:.4g}', textAnchor='end',
            fontSize=7, fillColor=GREY
        ))

    if asignado is not None:
        y = Y(asignado)
        d.add(Line(
            left, y, width-right, y,
            strokeColor=GREEN, strokeWidth=1.5,
            strokeDashArray=[5, 3]
        ))

    for i, (codigo, r1, r2, promedio) in enumerate(datos):
        x = X(i)
        if r1 is not None and r2 is not None:
            d.add(Line(
                x, Y(r1), x, Y(r2),
                strokeColor=colors.HexColor('#93A6B2'),
                strokeWidth=1.2
            ))

        for v, color, offset in (
            (r1, '#95A8B6', -3),
            (r2, '#95A8B6', 3)
        ):
            if v is not None:
                d.add(Circle(
                    x+offset, Y(v), 2.5,
                    fillColor=colors.HexColor(color),
                    strokeColor=None
                ))

        if promedio is not None:
            d.add(Circle(
                x, Y(promedio), 3.7,
                fillColor=GREEN,
                strokeColor=colors.white,
                strokeWidth=.7
            ))

        d.add(String(
            x, 18, codigo,
            textAnchor='middle', fontSize=6.5,
            fillColor=GREY
        ))

    d.add(String(
        left, height-7,
        f'Resultados ({unidad}) | Verde: promedio; gris: duplicados; línea: mediana',
        fontSize=8, fillColor=GREEN
    ))
    return d


def _grafica_z(filas, valor_asignado, sigma):
    datos = [
        (
            str(f.get('codigo_anonimo', '')),
            _evaluacion(f, valor_asignado, sigma)[1]
        )
        for f in filas
    ]
    if not any(z is not None for _, z in datos):
        return None

    width, height = 480, 180
    d = Drawing(width, height)
    left, right, bottom, top = 42, 12, 33, 15
    extremo = max(
        3.5,
        max(abs(z) for _, z in datos if z is not None) * 1.12
    )

    def Y(z):
        return bottom + (z + extremo) / (2 * extremo) * (height-bottom-top)

    for limit in (-3, -2, 0, 2, 3):
        color = (
            colors.HexColor('#B94A48') if abs(limit) == 3 else
            colors.HexColor('#D49C37') if abs(limit) == 2 else GREY
        )
        d.add(Line(
            left, Y(limit), width-right, Y(limit),
            strokeColor=color,
            strokeWidth=1 if limit else .7,
            strokeDashArray=[4, 3] if limit else None
        ))
        d.add(String(
            left-6, Y(limit)-2, str(limit),
            textAnchor='end', fontSize=8, fillColor=color
        ))

    step = (width-left-right) / max(len(datos), 1)
    for i, (codigo, z) in enumerate(datos):
        x = left + (i+.5)*step
        if z is not None:
            color = (
                '#116B48' if abs(z) <= 2 else
                '#D49C37' if abs(z) < 3 else
                '#B94A48'
            )
            y0, y1 = Y(0), Y(z)
            d.add(Rect(
                x-min(step*.30, 11),
                min(y0, y1),
                min(step*.60, 22),
                max(abs(y1-y0), .5),
                fillColor=colors.HexColor(color),
                strokeColor=None
            ))
        d.add(String(
            x, 17, codigo,
            textAnchor='middle', fontSize=6.5,
            fillColor=GREY
        ))

    d.add(String(
        left, height-7,
        'Puntuación z | Límites de advertencia ±2 y acción ±3',
        fontSize=8, fillColor=GREEN
    ))
    return d


def _grafica_consolidado(totals):
    categorias = [
        ('Satisfactorio', GREEN),
        ('Cuestionable', colors.HexColor('#D49C37')),
        ('No satisfactorio', colors.HexColor('#B94A48'))
    ]
    d = Drawing(480, 104)
    maximum = max(1, *(totals[k] for k, _ in categorias))

    for i, (cat, color) in enumerate(categorias):
        y = 80-i*29
        d.add(String(8, y+4, cat, fontSize=9, fillColor=GREY))
        d.add(Rect(
            125, y,
            305*totals[cat]/maximum, 14,
            fillColor=color, strokeColor=None
        ))
        d.add(String(
            438, y+4, str(totals[cat]),
            fontSize=9, fillColor=GREY
        ))
    return d


def generar_informe_global_pdf(
    campana: dict,
    materiales: list[dict],
    participantes: list[str]
) -> bytes:
    """Genera PDF preliminar con todos los materiales y ensayos.

    Las filas deben contener codigo_anonimo, sin identificadores internos.
    """
    if not isinstance(campana, dict) or not campana.get('codigo'):
        raise ValueError('Falta la identificación de la campaña.')
    if not materiales or not isinstance(materiales, list):
        raise ValueError('La campaña debe contener al menos un material.')

    for material in materiales:
        for ensayo in material.get('ensayos', []):
            for fila in ensayo.get('resultados', []):
                if any(
                    campo in fila
                    for campo in ('id_usuario', 'nombre_usuario', 'nombre')
                ):
                    raise ValueError(
                        'El informe requiere filas anonimizadas.'
                    )
                if not fila.get('codigo_anonimo'):
                    raise ValueError(
                        'Falta el código anónimo de un participante.'
                    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='GlobalTitle', parent=styles['Title'],
        textColor=GREEN, fontSize=17, leading=21,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='GlobalH', parent=styles['Heading2'],
        textColor=GREEN, fontSize=11, leading=15,
        spaceBefore=13, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='GlobalSmall', parent=styles['Normal'],
        fontSize=8, leading=12
    ))
    styles.add(ParagraphStyle(
        name='GlobalNotice', parent=styles['Normal'],
        fontSize=10, leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#A33636')
    ))

    story = [
        Paragraph(
            'PROVICHECK | Informe global de Pruebas de Aptitud',
            styles['GlobalTitle']
        ),
        Paragraph(
            'INFORME PRELIMINAR — REQUIERE REVISIÓN Y APROBACIÓN',
            styles['GlobalNotice']
        ),
        Spacer(1, 8*mm),
        Paragraph('1. Información general de la campaña', styles['GlobalH'])
    ]

    info = [
        ['Código', _safe(campana.get('codigo'))],
        ['Título', _safe(campana.get('titulo'))],
        ['Apertura', _safe(campana.get('fecha_apertura'))],
        ['Cierre', _safe(campana.get('fecha_cierre'))],
        ['Generado', datetime.now().strftime('%Y-%m-%d %H:%M')],
        ['Materiales', str(len(materiales))],
        ['Ensayos', str(sum(
            len(m.get('ensayos', [])) for m in materiales
        ))],
        [
            'Metodología σpt',
            Paragraph(
                _safe(campana.get(
                    'metodologia_sigma', 'No especificada'
                )),
                styles['GlobalSmall']
            )
        ],
    ]

    story.append(_table(info, [42*mm, 128*mm], header=False))
    story.append(Paragraph(
        'Participantes registrados en la campaña',
        styles['GlobalH']
    ))

    if participantes:
        for name in sorted(set(
            str(n).strip() for n in participantes if str(n).strip()
        )):
            story.append(Paragraph(
                '• ' + _safe(name), styles['GlobalSmall']
            ))
    else:
        story.append(Paragraph(
            'Listado de participantes no disponible.',
            styles['GlobalSmall']
        ))

    story.append(Paragraph(
        '2. Metodología estadística', styles['GlobalH']
    ))
    story.append(Paragraph(
        'Cada participante aporta dos determinaciones por ensayo. '
        'El valor asignado es la mediana de los promedios de participantes '
        'con duplicados completos. La puntuación z se calcula como '
        '(promedio − valor asignado) / σpt, cuando existe una σpt '
        'técnicamente aprobada. '
        'Criterios: |z| ≤ 2 satisfactorio; '
        '2 &lt; |z| &lt; 3 cuestionable; '
        '|z| ≥ 3 no satisfactorio. '
        'Los ensayos sin σpt aprobada quedan sin clasificación oficial.',
        styles['GlobalSmall']
    ))

    totals = Counter()
    preliminares = Counter()

    for mi, material in enumerate(materiales, 1):
        story.append(Paragraph(
            f'3.{mi}. Material: {_safe(material.get("nombre", "Sin nombre"))}',
            styles['GlobalH']
        ))
        ensayos = material.get('ensayos') or []

        if not ensayos:
            story.append(Paragraph(
                'No hay ensayos registrados para este material.',
                styles['GlobalSmall']
            ))

        for ei, report in enumerate(ensayos, 1):
            title = (
                f'{mi}.{ei} {_safe(report.get("parametro"))} '
                f'({_safe(report.get("unidad") or "sin unidad")})'
            )
            story.append(Paragraph(title, styles['GlobalH']))

            sigma = _number(report.get('desviacion_evaluacion'))
            asignado = _number(report.get('valor_asignado_mediana'))
            approved = bool(report.get('sigma_pt_aprobada', False))

            if sigma is not None and sigma > 0 and not approved:
                story.append(Paragraph(
                    'Evaluación z PRELIMINAR: σpt pendiente de aprobación '
                    'técnica. No constituye clasificación oficial.',
                    styles['GlobalSmall']
                ))
            elif sigma is None or sigma <= 0:
                story.append(Paragraph(
                    'σpt pendiente: evaluación sin clasificación.',
                    styles['GlobalSmall']
                ))

            details = [
                [
                    'Valor asignado (mediana)',
                    _fmt(asignado)
                ],
                [
                    'σpt utilizada (' +
                    ('aprobada' if approved else 'preliminar') + ')',
                    _fmt(sigma) if sigma is not None and sigma > 0
                    else 'Pendiente'
                ],
                [
                    'Desv. resultados individuales',
                    _fmt(report.get(
                        'desviacion_resultados_individuales',
                        report.get('desviacion_observada_muestral')
                    ))
                ],
                [
                    'Desv. promedios participantes',
                    _fmt(report.get(
                        'desviacion_promedios_participantes'
                    ))
                ],
                [
                    'Participantes con duplicados',
                    str(report.get(
                        'participantes_con_duplicados_completos'
                    ) or 0)
                ],
            ]

            story.append(_table(
                details, [82*mm, 88*mm], header=False
            ))

            rows = [[
                'Código', 'Resultado 1', 'Resultado 2',
                'Promedio', 'z', 'Clasificación'
            ]]
            filas = report.get('resultados') or []

            for fila in filas:
                promedio, z, category = _evaluacion(
                    fila, asignado, sigma
                )

                if category in (
                    'Satisfactorio',
                    'Cuestionable',
                    'No satisfactorio'
                ):
                    if approved:
                        totals[category] += 1
                    else:
                        preliminares[category] += 1

                rows.append([
                    _safe(fila['codigo_anonimo']),
                    _fmt(fila.get('resultado_1')),
                    _fmt(fila.get('resultado_2')),
                    _fmt(promedio),
                    _fmt(z) if z is not None else '—',
                    _safe(category)
                ])

            if len(rows) == 1:
                rows.append([
                    'Sin resultados', '—', '—', '—', '—', '—'
                ])

            story.append(_table(
                rows,
                [24*mm, 28*mm, 28*mm, 27*mm, 16*mm, 47*mm]
            ))

            grafica = _grafica_resultados(
                filas, asignado,
                str(report.get('unidad') or '')
            )
            if grafica is not None:
                story.append(Spacer(1, 3*mm))
                story.append(grafica)

            grafica_z = _grafica_z(filas, asignado, sigma)
            if grafica_z is not None:
                story.append(Spacer(1, 3*mm))
                story.append(grafica_z)

            story.append(Spacer(1, 4*mm))

    story.append(Paragraph(
        '4. Consolidado general', styles['GlobalH']
    ))

    summary = [['Categoría', 'Evaluaciones']]
    for cat in (
        'Satisfactorio',
        'Cuestionable',
        'No satisfactorio'
    ):
        summary.append([cat, str(totals[cat])])

    story.append(_table(
        summary, [110*mm, 60*mm]
    ))
    story.append(_grafica_consolidado(totals))

    if sum(preliminares.values()):
        story.append(Paragraph(
            'Evaluaciones PRELIMINARES (σpt sin aprobación técnica):',
            styles['GlobalH']
        ))
        prelim = [['Categoría', 'Evaluaciones preliminares']]
        for cat in (
            'Satisfactorio',
            'Cuestionable',
            'No satisfactorio'
        ):
            prelim.append([cat, str(preliminares[cat])])

        story.append(_table(
            prelim, [110*mm, 60*mm]
        ))
        story.append(_grafica_consolidado(preliminares))

    story.append(Paragraph(
        'Las cantidades corresponden a evaluaciones '
        'participante–ensayo, no a personas únicas. '
        'Las clasificaciones provisionales se excluyen '
        'del consolidado oficial.',
        styles['GlobalSmall']
    ))

    story.append(Paragraph(
        '5. Revisión y aprobación', styles['GlobalH']
    ))
    story.append(Paragraph(
        'Revisado por: _______________________    '
        'Fecha: ______________',
        styles['GlobalSmall']
    ))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        'Aprobado por: _______________________    '
        'Fecha: ______________',
        styles['GlobalSmall']
    ))
    story.append(Paragraph(
        'Documento preliminar. No contiene la relación '
        'confidencial entre códigos y nombres.',
        styles['GlobalSmall']
    ))

    doc.build(story)
    return buffer.getvalue()
