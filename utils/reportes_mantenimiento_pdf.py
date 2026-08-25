from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, PageBreak,
)


def _txt(valor: Any, defecto: str = "-") -> str:
    if valor is None:
        return defecto
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return defecto
    return texto


def _dinero(valor: Any) -> str:
    try:
        return f"$ {float(valor or 0):,.0f}"
    except (TypeError, ValueError):
        return "$ 0"


def _numero(valor: Any, decimales: int = 2) -> str:
    try:
        return f"{float(valor or 0):,.{decimales}f}"
    except (TypeError, ValueError):
        return f"{0:.{decimales}f}"


def generar_informe_mantenimientos_pdf(
    equipo: dict,
    mantenimientos: pd.DataFrame,
    fecha_inicial: Any,
    fecha_final: Any,
    usuario_emision: str = "",
    logo_path: Optional[Path] = None,
    version_sistema: str = "1.0",
) -> bytes:
    if mantenimientos is None or mantenimientos.empty:
        raise ValueError("No hay mantenimientos para generar el informe.")

    datos = mantenimientos.copy()
    if "fecha_inicio" in datos.columns:
        datos["_fecha"] = pd.to_datetime(datos["fecha_inicio"], errors="coerce")
        datos = datos.sort_values(["_fecha", "id"] if "id" in datos.columns else ["_fecha"])

    buffer = BytesIO()
    pagina = landscape(A4)
    margen = 12 * mm

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloPC", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=4,
    )
    subtitulo = ParagraphStyle(
        "SubtituloPC", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=12, alignment=TA_CENTER,
    )
    seccion = ParagraphStyle(
        "SeccionPC", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, spaceBefore=7, spaceAfter=5,
    )
    normal = ParagraphStyle(
        "NormalPC", parent=styles["Normal"], fontSize=7.5, leading=9.5,
    )
    pequeno = ParagraphStyle(
        "PequenoPC", parent=styles["Normal"], fontSize=6.7, leading=8.3,
    )
    centro = ParagraphStyle(
        "CentroPC", parent=pequeno, alignment=TA_CENTER,
    )
    derecha = ParagraphStyle(
        "DerechaPC", parent=pequeno, alignment=TA_RIGHT,
    )

    def pie_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(margen, 7 * mm, f"PROVICHECK v{version_sistema} - Informe histórico de mantenimiento")
        canvas.drawRightString(pagina[0] - margen, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        buffer, pagesize=pagina,
        leftMargin=margen, rightMargin=margen,
        topMargin=12 * mm, bottomMargin=13 * mm,
        title="PROVICHECK - Informe Histórico de Mantenimiento",
        author="PROVICHECK",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="mantenimiento", frames=frame, onPage=pie_pagina))

    story = []
    story.append(Paragraph("PROVICHECK", titulo))
    story.append(Paragraph("INFORME HISTÓRICO DE MANTENIMIENTO", subtitulo))
    story.append(Spacer(1, 4 * mm))

    codigo = _txt(equipo.get("codigo_equipo"))
    nombre = _txt(equipo.get("nombre_equipo"))
    info = [
        [Paragraph("<b>Equipo</b>", pequeno), Paragraph(f"{codigo} - {nombre}", pequeno),
         Paragraph("<b>Laboratorio</b>", pequeno), Paragraph(_txt(equipo.get("laboratorio")), pequeno)],
        [Paragraph("<b>Marca / Modelo</b>", pequeno), Paragraph(f"{_txt(equipo.get('marca'))} / {_txt(equipo.get('modelo'))}", pequeno),
         Paragraph("<b>Serie</b>", pequeno), Paragraph(_txt(equipo.get("serie")), pequeno)],
        [Paragraph("<b>Ubicación</b>", pequeno), Paragraph(_txt(equipo.get("ubicacion")), pequeno),
         Paragraph("<b>Responsable</b>", pequeno), Paragraph(_txt(equipo.get("responsable")), pequeno)],
        [Paragraph("<b>Periodo</b>", pequeno), Paragraph(f"{_txt(fecha_inicial)} a {_txt(fecha_final)}", pequeno),
         Paragraph("<b>Emitido por</b>", pequeno), Paragraph(_txt(usuario_emision), pequeno)],
    ]
    tinfo = Table(info, colWidths=[28*mm, 86*mm, 28*mm, 105*mm])
    tinfo.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#B8C2CC")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EEF3F8")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#EEF3F8")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tinfo)

    costo_rep = pd.to_numeric(datos.get("costo_repuesto", 0), errors="coerce").fillna(0).sum() if "costo_repuesto" in datos else 0
    costo_mo = pd.to_numeric(datos.get("costo_mano_obra", 0), errors="coerce").fillna(0).sum() if "costo_mano_obra" in datos else 0
    costo_otros = pd.to_numeric(datos.get("costo_otros", 0), errors="coerce").fillna(0).sum() if "costo_otros" in datos else 0
    costo_total = pd.to_numeric(datos.get("costo_total", 0), errors="coerce").fillna(0).sum() if "costo_total" in datos else costo_rep + costo_mo + costo_otros
    horas = pd.to_numeric(datos.get("horas_fuera_servicio", 0), errors="coerce").fillna(0).sum() if "horas_fuera_servicio" in datos else 0
    preventivos = int((datos.get("tipo_mantenimiento", pd.Series(dtype=str)).astype(str) == "Preventivo").sum())
    correctivos = int((datos.get("tipo_mantenimiento", pd.Series(dtype=str)).astype(str) == "Correctivo").sum())

    story.append(Paragraph("Resumen del periodo", seccion))
    resumen = [
        ["Intervenciones", "Preventivos", "Correctivos", "Costo repuestos", "Mano de obra", "Otros costos", "Costo total", "Horas fuera servicio"],
        [str(len(datos)), str(preventivos), str(correctivos), _dinero(costo_rep), _dinero(costo_mo), _dinero(costo_otros), _dinero(costo_total), _numero(horas)],
    ]
    tres = Table(resumen, colWidths=[28*mm, 26*mm, 26*mm, 35*mm, 35*mm, 32*mm, 35*mm, 37*mm], repeatRows=1)
    tres.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCE6F1")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6.8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#AAB4BE")),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(tres)

    story.append(Paragraph("Detalle de mantenimientos", seccion))
    encabezados = ["Fecha", "Tipo / Estado", "Descripción / Acción", "Ejecutor / Proveedor", "Repuesto / componente", "Orden", "Costos", "Resultado"]
    tabla = [[Paragraph(f"<b>{h}</b>", centro) for h in encabezados]]

    for _, r in datos.iterrows():
        fecha = _txt(r.get("fecha_inicio"))
        if _txt(r.get("fecha_fin"), ""):
            fecha += f"<br/><font size='6'>Fin: {_txt(r.get('fecha_fin'))}</font>"
        tipo_estado = f"<b>{_txt(r.get('tipo_mantenimiento'))}</b><br/>{_txt(r.get('estado_mantenimiento'))}"
        desc_acc = f"<b>Descripción:</b> {_txt(r.get('descripcion'))}<br/><b>Acción:</b> {_txt(r.get('accion_realizada'))}<br/><b>Causa:</b> {_txt(r.get('causa'))}"
        ejecutor = f"{_txt(r.get('realizado_por_tipo'))}<br/><b>Responsable:</b> {_txt(r.get('responsable'))}<br/><b>Proveedor:</b> {_txt(r.get('proveedor'))}"
        componente = f"{_txt(r.get('componente'))}<br/>{_txt(r.get('marca_componente'))} / {_txt(r.get('modelo_componente'))}<br/><b>Serie/Lote:</b> {_txt(r.get('serie_componente'))} · <b>Cant.:</b> {_txt(r.get('cantidad'), '1')}"
        costos = f"Rep.: {_dinero(r.get('costo_repuesto'))}<br/>M.O.: {_dinero(r.get('costo_mano_obra'))}<br/>Otros: {_dinero(r.get('costo_otros'))}<br/><b>Total: {_dinero(r.get('costo_total'))}</b>"
        resultado = f"{_txt(r.get('resultado'))}<br/><b>Fuera servicio:</b> {_numero(r.get('horas_fuera_servicio'))} h"
        if _txt(r.get("observaciones"), ""):
            resultado += f"<br/><b>Obs.:</b> {_txt(r.get('observaciones'))}"
        tabla.append([
            Paragraph(fecha, pequeno), Paragraph(tipo_estado, pequeno), Paragraph(desc_acc, pequeno),
            Paragraph(ejecutor, pequeno), Paragraph(componente, pequeno), Paragraph(_txt(r.get("numero_orden")), pequeno),
            Paragraph(costos, pequeno), Paragraph(resultado, pequeno),
        ])

    tdet = Table(tabla, colWidths=[20*mm, 29*mm, 61*mm, 43*mm, 45*mm, 22*mm, 33*mm, 40*mm], repeatRows=1)
    tdet.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCE6F1")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1F2937")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#B7C0C8")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tdet)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Nota: este informe consolida los mantenimientos activos registrados en PROVICHECK dentro del periodo seleccionado. Los costos corresponden a los valores consignados en cada registro.",
        pequeno,
    ))

    doc.build(story)
    return buffer.getvalue()