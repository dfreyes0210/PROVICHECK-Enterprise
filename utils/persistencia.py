from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook
from config import EXCEL_PATH


def generar_id_sesion(codigo_equipo):
    ahora = datetime.now()
    return f"SES-{codigo_equipo}-{ahora.strftime('%Y%m%d-%H%M%S')}"


def guardar_verificacion_excel(datos):
    archivo = Path(EXCEL_PATH)

    if not archivo.exists():
        return False, "No se encontró el archivo Excel maestro."

    wb = load_workbook(archivo)

    if "Verificaciones" not in wb.sheetnames:
        return False, "No existe la hoja Verificaciones."

    ws = wb["Verificaciones"]
    headers = [cell.value for cell in ws[1]]

    columnas_nuevas = [
        "id_sesion",
        "hora_verificacion",
        "estado_verificacion",
        "estado_punto",
        "motivo_no_evaluado",
    ]

    for columna in columnas_nuevas:
        if columna not in headers:
            ws.cell(row=1, column=len(headers) + 1).value = columna
            headers.append(columna)

    fila = [datos.get(columna, "") for columna in headers]

    ws.append(fila)
    wb.save(archivo)

    return True, "Verificación guardada correctamente."