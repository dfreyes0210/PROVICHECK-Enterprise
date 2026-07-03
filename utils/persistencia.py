from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook

from config import EXCEL_PATH


def generar_id_sesion(codigo_equipo):
    ahora = datetime.now()
    return f"SES-{codigo_equipo}-{ahora.strftime('%Y%m%d-%H%M%S')}"


def guardar_verificacion_excel(datos):
    """
    Guarda una verificación en la hoja Verificaciones del Excel maestro.
    """
    archivo = Path(EXCEL_PATH)

    if not archivo.exists():
        return False, "No se encontró el archivo Excel maestro."

    wb = load_workbook(archivo)

    if "Verificaciones" not in wb.sheetnames:
        return False, "No existe la hoja Verificaciones en el Excel."

    ws = wb["Verificaciones"]

    headers = [cell.value for cell in ws[1]]

    # Agregar columnas nuevas si no existen
    columnas_nuevas = ["id_sesion", "hora_verificacion", "estado_verificacion"]

    for columna in columnas_nuevas:
        if columna not in headers:
            ws.cell(row=1, column=len(headers) + 1).value = columna
            headers.append(columna)

    nueva_fila = []

    for columna in headers:
        nueva_fila.append(datos.get(columna, ""))

    ws.append(nueva_fila)
    wb.save(archivo)

    return True, "Verificación guardada correctamente."