def evaluar_resultado(resultado_observado, valor_nominal, limite_inferior, limite_superior):
    resultado = limpiar_numero(resultado_observado)
    nominal = limpiar_numero(valor_nominal)
    tolerancia_inferior = limpiar_numero(limite_inferior)
    tolerancia_superior = limpiar_numero(limite_superior)

    if resultado is None:
        return {
            "resultado": resultado_observado,
            "valor_nominal": nominal,
            "error": None,
            "limite_inferior_real": None,
            "limite_superior_real": None,
            "cumple": False,
            "estado": "Sin resultado",
            "mensaje": "No se ingresó un resultado válido."
        }

    error = None
    if nominal is not None:
        error = resultado - nominal

    if nominal is None or tolerancia_inferior is None or tolerancia_superior is None:
        return {
            "resultado": resultado,
            "valor_nominal": nominal,
            "error": error,
            "limite_inferior_real": None,
            "limite_superior_real": None,
            "cumple": None,
            "estado": "Sin límites",
            "mensaje": "El punto no tiene valor nominal o límites configurados."
        }

    limite_inferior_real = nominal + tolerancia_inferior
    limite_superior_real = nominal + tolerancia_superior

    cumple = limite_inferior_real <= resultado <= limite_superior_real

    return {
        "resultado": resultado,
        "valor_nominal": nominal,
        "error": error,
        "limite_inferior_real": limite_inferior_real,
        "limite_superior_real": limite_superior_real,
        "tolerancia_inferior": tolerancia_inferior,
        "tolerancia_superior": tolerancia_superior,
        "cumple": cumple,
        "estado": "Cumple" if cumple else "No cumple",
        "mensaje": "Resultado dentro de límites reales." if cumple else "Resultado fuera de límites reales."
    }