import math


def formatear_numero(valor, decimales=4):
    try:
        if valor is None:
            return "-"

        numero = float(valor)

        if math.isnan(numero):
            return "-"

        return f"{numero:.{decimales}f}"
    except Exception:
        return "-"