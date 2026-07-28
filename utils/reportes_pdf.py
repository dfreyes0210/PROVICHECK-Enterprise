from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


VERDE_PROVIDENCIA = colors.HexColor("#62B32E")
VERDE_OSCURO = colors.HexColor("#317A20")
AZUL_TEXTO = colors.HexColor("#0F2747")
GRIS_FONDO = colors.HexColor("#F3F6F9")
GRIS_LINEA = colors.HexColor("#CBD8E8")
ROJO = colors.HexColor("#C62828")
AMARILLO = colors.HexColor("#D99A00")


def _texto(valor: Any, por_defecto: str = "No registrado") -> str:
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def _numero(valor: Any, decimales: int = 4) -> str:
    try:
        numero = float(valor)
        if pd.isna(numero):
            return "-"
        return f"{numero:.{decimales}f}"
    except (TypeError, ValueError):
        return "-"


def _crear_grafica_tendencia(
    datos: pd.DataFrame,
    titulo: str,
    unidad: str,
) -> BytesIO:
    buffer = BytesIO()
    figura, eje = plt.subplots(figsize=(11.2, 4.8))

    eje.plot(
        datos["fecha_hora"],
        datos["resultado"],
        marker="o",
        linewidth=1.8,
        label="Resultado observado",
    )
    eje.plot(
        datos["fecha_hora"],
        datos["valor_nominal"],
        linewidth=1.4,
        label="Valor nominal",
    )
    eje.plot(
        datos["fecha_hora"],
        datos["limite_superior"],
        linestyle="--",
        linewidth=1.2,
        label="Limite superior",
    )
    eje.plot(
        datos["fecha_hora"],
        datos["limite_inferior"],
        linestyle="--",
        linewidth=1.2,
        label="Limite inferior",
    )

    if "estado_punto" in datos.columns:
        no_conformes = datos[
            datos["estado_punto"].astype(str).str.lower().eq("no cumple")
        ]
        if not no_conformes.empty:
            eje.scatter(
                no_conformes["fecha_hora"],
                no_conformes["resultado"],
                s=55,
                zorder=5,
                label="Fuera de tolerancia",
            )

    eje.set_title(titulo, fontsize=13, fontweight="bold")
    eje.set_xlabel("Fecha y hora")
    eje.set_ylabel(f"Resultado ({unidad})" if unidad else "Resultado")
    eje.grid(True, alpha=0.25)
    eje.legend(loc="best", fontsize=8)
    figura.autofmt_xdate()
    figura.tight_layout()
    figura.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close(figura)
    buffer.seek(0)
    return buffer


def _estadisticos(datos: pd.DataFrame) -> dict[str, Any]:
    resultados = pd.to_numeric(datos["resultado"], errors="coerce").dropna()
    errores = pd.to_numeric(datos["error"], errors="coerce").dropna()

    total = len(datos)
    conformes = int(
        datos["estado_punto"].astype(str).str.lower().eq("cumple").sum()
    )
    no_conformes = int(
        datos["estado_punto"].astype(str).str.lower().eq("no cumple").sum()
    )
    no_evaluados = int(
        datos["estado_punto"].astype(str).str.lower().eq("no evaluado").sum()
    )
    cumplimiento = (conformes / total * 100) if total else 0.0

    return {
        "total": total,
        "promedio": resultados.mean() if not resultados.empty else None,
        "desviacion": (
            resultados.std(ddof=1) if len(resultados) > 1 else 0.0
        ),
        "minimo": resultados.min() if not resultados.empty else None,
        "maximo": resultados.max() if not resultados.empty else None,
        "error_promedio": errores.mean() if not errores.empty else None,
        "conformes": conformes,
        "no_conformes": no_conformes,
        "no_evaluados": no_evaluados,
        "cumplimiento": cumplimiento,
    }


def generar_informe_tendencia_pdf(
    equipo: dict[str, Any],
    patron: dict[str, Any],
    datos: pd.DataFrame,
    fecha_inicial,
    fecha_final,
    usuario_emision: str,
    logo_path: str | Path | None = None,
    version_sistema: str = "1.0",
) -> bytes:
    if datos.empty:
        raise ValueError("No hay datos para generar el informe.")

    datos = datos.copy()
    datos["fecha_hora"] = pd.to_datetime(
        datos["fecha_hora"],
        errors="coerce",
    )
    datos = datos.dropna(subset=["fecha_hora"]).sort_values("fecha_hora")

    if datos.empty:
        raise ValueError("No hay fechas validas para generar el informe.")

    unidad = _texto(
        patron.get("unidad") or equipo.get("unidad"),
        "",
    )
    punto = _texto(datos.iloc[0].get("punto"), "Punto de verificacion")
    codigo_patron = _texto(patron.get("codigo_patron"))
    emision = datetime.now(ZoneInfo("America/Bogota"))
    estad = _estadisticos(datos)

    grafica = _crear_grafica_tendencia(
        datos,
        f"Tendencia historica - {punto}",
        unidad,
    )

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=19 * mm,
        bottomMargin=17 * mm,
        title=f"Informe de tendencias - {equipo.get('codigo_equipo', '')}",
        author="PROVICHECK Enterprise",
    )

    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloProvidencia",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=AZUL_TEXTO,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SubtituloProvidencia",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=VERDE_OSCURO,
            alignment=TA_CENTER,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SeccionProvidencia",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.white,
            backColor=VERDE_OSCURO,
            borderPadding=(5, 7, 5, 7),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="TextoPequeno",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=AZUL_TEXTO,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="Pie",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            textColor=colors.HexColor("#52657A"),
            alignment=TA_CENTER,
        )
    )

    elementos = []

    encabezado_datos = []
    ruta_logo = Path(logo_path) if logo_path else None
    if ruta_logo and ruta_logo.exists():
        encabezado_datos.append(
            Image(str(ruta_logo), width=58 * mm, height=12.5 * mm)
        )
    else:
        encabezado_datos.append(
            Paragraph("<b>PROVIDENCIA</b>", estilos["TituloProvidencia"])
        )

    encabezado_datos.append(
        Paragraph(
            "PROVICHECK ENTERPRISE<br/>"
            "<font size='13'><b>INFORME DE TENDENCIAS DE VERIFICACION</b></font>",
            estilos["SubtituloProvidencia"],
        )
    )
    encabezado_datos.append(
        Paragraph(
            f"<b>Emision</b><br/>{emision.strftime('%d/%m/%Y')}<br/>"
            f"{emision.strftime('%H:%M:%S')}<br/>"
            f"<b>Version</b> {version_sistema}",
            ParagraphStyle(
                "Emision",
                parent=estilos["TextoPequeno"],
                alignment=TA_RIGHT,
            ),
        )
    )

    tabla_encabezado = Table(
        [encabezado_datos],
        colWidths=[65 * mm, 142 * mm, 55 * mm],
    )
    tabla_encabezado.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 2, VERDE_PROVIDENCIA),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elementos.append(tabla_encabezado)
    elementos.append(Spacer(1, 4 * mm))

    elementos.append(
        Paragraph("1. Informacion del equipo", estilos["SeccionProvidencia"])
    )

    equipo_tabla = [
        ["Codigo", _texto(equipo.get("codigo_equipo")),
         "Equipo", _texto(equipo.get("nombre_equipo"))],
        ["Marca", _texto(equipo.get("marca")),
         "Modelo", _texto(equipo.get("modelo"))],
        ["Serie", _texto(equipo.get("serie")),
         "Laboratorio", _texto(equipo.get("laboratorio"))],
        ["Ubicacion", _texto(equipo.get("ubicacion")),
         "Responsable", _texto(equipo.get("responsable"))],
    ]
    tabla_equipo = Table(
        equipo_tabla,
        colWidths=[28 * mm, 60 * mm, 28 * mm, 146 * mm],
    )
    tabla_equipo.setStyle(_estilo_tabla_ficha())
    elementos.append(tabla_equipo)

    elementos.append(
        Paragraph("2. Informacion del patron", estilos["SeccionProvidencia"])
    )
    patron_tabla = [
        ["Codigo", codigo_patron,
         "Descripcion", _texto(patron.get("descripcion"))],
        ["Marca", _texto(patron.get("marca")),
         "Valor nominal",
         f"{_numero(patron.get('valor_nominal_g'))} {unidad}".strip()],
        ["Vencimiento", _texto(patron.get("fecha_vencimiento_calibracion")),
         "Estado", _texto(patron.get("estado"))],
        ["Punto analizado", punto,
         "Periodo",
         f"{fecha_inicial.strftime('%d/%m/%Y')} al "
         f"{fecha_final.strftime('%d/%m/%Y')}"],
    ]
    tabla_patron = Table(
        patron_tabla,
        colWidths=[28 * mm, 60 * mm, 28 * mm, 146 * mm],
    )
    tabla_patron.setStyle(_estilo_tabla_ficha())
    elementos.append(tabla_patron)

    elementos.append(
        Paragraph("3. Resumen estadistico", estilos["SeccionProvidencia"])
    )
    resumen = [
        ["Registros", str(estad["total"]),
         "Promedio", _numero(estad["promedio"]),
         "Desv. estandar", _numero(estad["desviacion"]),
         "Cumplimiento", f"{estad['cumplimiento']:.1f}%"],
        ["Conformes", str(estad["conformes"]),
         "No conformes", str(estad["no_conformes"]),
         "No evaluados", str(estad["no_evaluados"]),
         "Error promedio", _numero(estad["error_promedio"])],
        ["Minimo", _numero(estad["minimo"]),
         "Maximo", _numero(estad["maximo"]),
         "", "", "", ""],
    ]
    tabla_resumen = Table(
        resumen,
        colWidths=[25 * mm, 25 * mm] * 4,
    )
    tabla_resumen.setStyle(_estilo_tabla_ficha())
    elementos.append(tabla_resumen)

    elementos.append(PageBreak())
    elementos.append(
        Paragraph("4. Grafica de tendencia", estilos["SeccionProvidencia"])
    )
    elementos.append(
        Image(grafica, width=257 * mm, height=105 * mm)
    )

    elementos.append(PageBreak())
    elementos.append(
        Paragraph("5. Tabla de resultados", estilos["SeccionProvidencia"])
    )

    columnas = [
        "Fecha",
        "Hora",
        "Resultado",
        "Error",
        "Limite inferior",
        "Limite superior",
        "Estado",
        "Responsable",
        "Observacion",
    ]
    filas = [columnas]

    for _, fila in datos.iterrows():
        filas.append(
            [
                _texto(fila.get("fecha"), "-"),
                _texto(fila.get("hora"), "-"),
                _numero(fila.get("resultado")),
                _numero(fila.get("error")),
                _numero(fila.get("limite_inferior")),
                _numero(fila.get("limite_superior")),
                _texto(fila.get("estado_punto"), "-"),
                _texto(fila.get("responsable"), "-"),
                Paragraph(
                    _texto(fila.get("observacion"), "-"),
                    estilos["TextoPequeno"],
                ),
            ]
        )

    tabla_resultados = Table(
        filas,
        repeatRows=1,
        colWidths=[
            22 * mm,
            18 * mm,
            24 * mm,
            22 * mm,
            25 * mm,
            25 * mm,
            24 * mm,
            37 * mm,
            65 * mm,
        ],
    )
    tabla_resultados.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VERDE_OSCURO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (2, 1), (5, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.35, GRIS_LINEA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FONDO]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_resultados)
    elementos.append(Spacer(1, 5 * mm))

    elementos.append(
        KeepTogether(
            [
                Paragraph(
                    "<b>Emitido automaticamente por PROVICHECK Enterprise</b><br/>"
                    "Sistema de gestion de equipos de laboratorio - Ingenio Providencia<br/>"
                    f"Usuario de emision: {_texto(usuario_emision)}<br/>"
                    f"Fecha y hora de emision: {emision.strftime('%d/%m/%Y %H:%M:%S')}",
                    estilos["Pie"],
                )
            ]
        )
    )

    def agregar_pie(canvas, doc):
        canvas.saveState()
        ancho, _ = landscape(A4)
        canvas.setStrokeColor(VERDE_PROVIDENCIA)
        canvas.setLineWidth(0.8)
        canvas.line(14 * mm, 12 * mm, ancho - 14 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#52657A"))
        canvas.drawString(
            14 * mm,
            7.5 * mm,
            "PROVICHECK Enterprise - Ingenio Providencia",
        )
        canvas.drawRightString(
            ancho - 14 * mm,
            7.5 * mm,
            f"Pagina {doc.page}",
        )
        canvas.restoreState()

    documento.build(
        elementos,
        onFirstPage=agregar_pie,
        onLaterPages=agregar_pie,
    )
    salida.seek(0)
    return salida.getvalue()


def _estilo_tabla_ficha() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (0, -1), GRIS_FONDO),
            ("BACKGROUND", (2, 0), (2, -1), GRIS_FONDO),
            ("TEXTCOLOR", (0, 0), (-1, -1), AZUL_TEXTO),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTNAME", (3, 0), (3, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS_LINEA),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )