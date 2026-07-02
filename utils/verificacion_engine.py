import math


def limpiar_numero(valor):
    try:
        if valor is None:
            return None

        if str(valor).strip() == "":
            return None

        numero = float(valor)

        if math.isnan(numero):
            return None

        return numero

    except Exception:
        return None


def obtener_puntos_equipo(puntos_df, codigo_equipo):
    if puntos_df.empty:
        return puntos_df

    df = puntos_df.copy()
    df["codigo_equipo"] = df["codigo_equipo"].astype(str)

    return df[df["codigo_equipo"] == str(codigo_equipo)]


def preparar_punto_para_verificacion(punto):
    valor_nominal = limpiar_numero(punto.get("valor_nominal_g"))
    limite_inferior = limpiar_numero(punto.get("limite_inferior_g"))
    limite_superior = limpiar_numero(punto.get("limite_superior_g"))

    return {
        "id_punto": punto.get("id_punto"),
        "codigo_equipo": punto.get("codigo_equipo"),
        "nombre_chequeo": punto.get("nombre_chequeo"),
        "punto_verificacion": punto.get("punto_verificacion"),
        "unidad": punto.get("unidad"),
        "valor_nominal": valor_nominal,
        "limite_inferior": limite_inferior,
        "limite_superior": limite_superior,
    }


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
            "cumple": None,
            "estado": "Sin resultado",
            "mensaje": "No se ingresó un resultado válido.",
        }

    error = resultado - nominal if nominal is not None else None

    if nominal is None or tolerancia_inferior is None or tolerancia_superior is None:
        return {
            "resultado": resultado,
            "valor_nominal": nominal,
            "error": error,
            "limite_inferior_real": None,
            "limite_superior_real": None,
            "cumple": None,
            "estado": "Sin límites",
            "mensaje": "Punto sin límites configurados.",
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
        "mensaje": "Resultado dentro de límites reales." if cumple else "Resultado fuera de límites reales.",
    }