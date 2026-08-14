from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.parse import urlencode

import qrcode
from PIL import Image
from reportlab.lib.pagesizes import portrait
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _texto_seguro(valor: Any, por_defecto: str = "") -> str:
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def _normalizar_codigo(valor: Any) -> str:
    texto = _texto_seguro(valor)

    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base

    return texto


def construir_url_equipo(
    base_url: str,
    codigo_equipo: Any,
) -> str:
    """
    Construye el enlace estable del QR.

    Ejemplo:
        https://mi-app.streamlit.app/?equipo=63065
    """
    base = _texto_seguro(base_url).rstrip("/")
    codigo = _normalizar_codigo(codigo_equipo)

    if not base:
        raise ValueError(
            "No se ha configurado la URL pública de PROVICHECK."
        )

    if not codigo:
        raise ValueError("El equipo no tiene un código válido.")

    return f"{base}/?{urlencode({'equipo': codigo})}"


def generar_qr_png(
    contenido: str,
    escala: int = 10,
    borde: int = 3,
) -> bytes:
    """
    Genera un QR PNG de alta legibilidad.
    """
    contenido = _texto_seguro(contenido)

    if not contenido:
        raise ValueError("El contenido del QR está vacío.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=max(4, int(escala)),
        border=max(2, int(borde)),
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    imagen = qr.make_image(
        fill_color="black",
        back_color="white",
    ).convert("RGB")

    salida = BytesIO()
    imagen.save(
        salida,
        format="PNG",
        optimize=True,
    )
    return salida.getvalue()


def generar_etiqueta_equipo_pdf(
    codigo_equipo: Any,
    nombre_equipo: str,
    qr_png: bytes,
    subtitulo: str = "Escanee para consultar el equipo en PROVICHECK",
) -> bytes:
    """
    Genera una etiqueta vertical de 6 x 8 cm lista para imprimir.

    Contenido:
      - PROVICHECK
      - QR
      - Código
      - Nombre del equipo
      - Mensaje de consulta
    """
    codigo = _normalizar_codigo(codigo_equipo)
    nombre = _texto_seguro(
        nombre_equipo,
        "Equipo sin nombre",
    )

    if not qr_png:
        raise ValueError("No se recibió la imagen QR.")

    ancho = 6 * cm
    alto = 8 * cm
    salida = BytesIO()

    pdf = canvas.Canvas(
        salida,
        pagesize=portrait((ancho, alto)),
    )

    margen = 0.28 * cm

    # Marco.
    pdf.setLineWidth(0.7)
    pdf.roundRect(
        margen,
        margen,
        ancho - 2 * margen,
        alto - 2 * margen,
        0.18 * cm,
        stroke=1,
        fill=0,
    )

    # Cabecera.
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(
        ancho / 2,
        alto - 0.78 * cm,
        "PROVICHECK",
    )

    pdf.setFont("Helvetica", 6.8)
    pdf.drawCentredString(
        ancho / 2,
        alto - 1.08 * cm,
        "Gestión y verificación de equipos",
    )

    # QR.
    imagen_qr = Image.open(BytesIO(qr_png))
    qr_side = 3.45 * cm
    qr_x = (ancho - qr_side) / 2
    qr_y = alto - 4.82 * cm

    from reportlab.lib.utils import ImageReader
    pdf.drawImage(
        ImageReader(imagen_qr),
        qr_x,
        qr_y,
        qr_side,
        qr_side,
        preserveAspectRatio=True,
        mask="auto",
    )

    # Código.
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawCentredString(
        ancho / 2,
        2.78 * cm,
        f"Código: {codigo}",
    )

    # Nombre, con máximo dos líneas.
    texto_nombre = nombre
    max_chars = 32
    lineas = []

    while texto_nombre:
        if len(texto_nombre) <= max_chars:
            lineas.append(texto_nombre)
            break

        corte = texto_nombre.rfind(" ", 0, max_chars)
        if corte <= 0:
            corte = max_chars

        lineas.append(texto_nombre[:corte].strip())
        texto_nombre = texto_nombre[corte:].strip()

        if len(lineas) == 2:
            if texto_nombre:
                lineas[-1] = (
                    lineas[-1][: max_chars - 3].rstrip()
                    + "..."
                )
            break

    pdf.setFont("Helvetica-Bold", 7.2)
    y_nombre = 2.38 * cm
    for linea in lineas[:2]:
        pdf.drawCentredString(
            ancho / 2,
            y_nombre,
            linea,
        )
        y_nombre -= 0.30 * cm

    # Pie.
    pdf.setFont("Helvetica", 6.2)
    pie = _texto_seguro(subtitulo)
    if len(pie) > 55:
        pie = pie[:52].rstrip() + "..."

    pdf.drawCentredString(
        ancho / 2,
        0.82 * cm,
        pie,
    )

    pdf.setFont("Helvetica", 5.7)
    pdf.drawCentredString(
        ancho / 2,
        0.53 * cm,
        "No retire ni modifique esta etiqueta",
    )

    pdf.showPage()
    pdf.save()

    return salida.getvalue()