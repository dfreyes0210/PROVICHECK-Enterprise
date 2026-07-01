def formatear_numero(valor, decimales=4):
    """
    Formatea un número con la cantidad de decimales indicada.
    Si el valor es None o inválido devuelve "-".
    """
    try:
        if valor is None:
            return "-"
        return f"{float(valor):.{decimales}f}"
    except Exception:
        return "-"