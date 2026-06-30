import pandas as pd


def limpiar_numero(valor):
    try:
        if pd.isna(valor):
            return None
        return float(valor)
    except Exception:
        return None


def obtener_puntos_equipo(puntos_df, codigo_equipo):
    if puntos_df.empty:
        return pd.DataFrame()

    df = puntos_df.copy()
    df["codigo_equipo"] = df["codigo_equipo"].astype(str)

    return df[df["codigo_equipo"] == str(codigo_equipo)]


def evaluar_resultado(resultado_observado, valor_nominal, limite_inferior, limite_superior):
    resultado = limpiar_numero(resultado_observado)
    nominal = limpiar_numero(valor_nominal)
    li = limpiar_numero(limite_inferior)
    ls = limpiar_numero(limite_superior)

    if resultado is None:
        return {
            "resultado": resultado_observado,
            "error": None,
            "cumple": False,
            "estado": "Sin resultado",
            "mensaje": "No se ingresó un resultado válido."
        }

    error = None
    if nominal is not None:
        error = resultado - nominal

    if li is None or ls is None:
        return {
            "resultado": resultado,
            "error": error,
            "cumple": None,
            "estado": "Sin límites",
            "mensaje": "El punto no tiene límites configurados."
        }

    cumple = li <= resultado <= ls

    return {
        "resultado": resultado,
        "error": error,
        "cumple": cumple,
        "estado": "Cumple" if cumple else "No cumple",
        "mensaje": "Resultado dentro de límites." if cumple else "Resultado fuera de límites."
    }


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