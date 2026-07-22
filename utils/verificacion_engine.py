import math

import pandas as pd


def limpiar_numero(valor):
    """Convierte un valor numérico de Excel/SQLite a float."""
    try:
        if valor is None:
            return None

        texto = str(valor).strip()

        if texto == "" or texto.lower() in {"nan", "none", "null"}:
            return None

        numero = float(valor)

        if math.isnan(numero) or math.isinf(numero):
            return None

        return numero

    except (TypeError, ValueError):
        return None


def _primer_valor(punto, *nombres):
    """Devuelve el primer valor disponible entre varios nombres de columna."""
    for nombre in nombres:
        if nombre in punto:
            valor = punto.get(nombre)

            if valor is not None and str(valor).strip() != "":
                return valor

    return None


def _normalizar_codigo(valor):
    """
    Normaliza códigos provenientes de Excel.

    Ejemplos:
    63065, 63065.0 y "63065" se comparan como "63065".
    """
    if valor is None:
        return ""

    texto = str(valor).strip()

    try:
        numero = float(texto)

        if numero.is_integer():
            return str(int(numero))

    except (TypeError, ValueError):
        pass

    return texto


def obtener_puntos_equipo(puntos_df, codigo_equipo):
    """Filtra los puntos configurados para el equipo seleccionado."""
    if puntos_df is None or puntos_df.empty:
        return pd.DataFrame()

    if "codigo_equipo" not in puntos_df.columns:
        return pd.DataFrame()

    df = puntos_df.copy()
    codigo_buscado = _normalizar_codigo(codigo_equipo)

    codigos_normalizados = df["codigo_equipo"].apply(_normalizar_codigo)

    resultado = df[codigos_normalizados == codigo_buscado].copy()

    if "id_punto" in resultado.columns:
        resultado = resultado.sort_values(
            by="id_punto",
            kind="stable",
        )

    return resultado.reset_index(drop=True)


def preparar_punto_para_verificacion(punto):
    """
    Prepara un punto usando límites absolutos.

    PROVICHECK almacena:
    - limite_inferior_g
    - valor_nominal_g
    - limite_superior_g

    Los límites inferior y superior ya representan el intervalo real,
    por lo que no se deben volver a sumar al valor nominal.
    """
    nominal = limpiar_numero(
        _primer_valor(
            punto,
            "valor_nominal_g",
            "valor_nominal",
            "nominal",
        )
    )

    limite_inferior = limpiar_numero(
        _primer_valor(
            punto,
            "limite_inferior_g",
            "limite_inferior",
            "li",
        )
    )

    limite_superior = limpiar_numero(
        _primer_valor(
            punto,
            "limite_superior_g",
            "limite_superior",
            "ls",
        )
    )

    desviacion = limpiar_numero(
        _primer_valor(
            punto,
            "desviacion_aceptada_g",
            "desviacion_aceptada",
            "tolerancia",
        )
    )

    # Respaldo: si faltan límites absolutos, se calculan con nominal ± desviación.
    if nominal is not None and desviacion is not None:
        if limite_inferior is None:
            limite_inferior = nominal - desviacion

        if limite_superior is None:
            limite_superior = nominal + desviacion

    decimales = _primer_valor(
        punto,
        "decimales",
        "numero_decimales",
    )

    try:
        decimales = int(decimales)
    except (TypeError, ValueError):
        decimales = 4

    decimales = max(0, min(decimales, 8))

    return {
        "id_punto": punto.get("id_punto"),
        "codigo_equipo": _normalizar_codigo(
            punto.get("codigo_equipo")
        ),
        "tipo_equipo": punto.get("tipo_equipo"),
        "nombre_chequeo": punto.get("nombre_chequeo"),
        "punto_verificacion": punto.get("punto_verificacion"),
        "unidad": punto.get("unidad"),
        "valor_nominal": nominal,
        "limite_inferior": limite_inferior,
        "limite_superior": limite_superior,
        "desviacion_aceptada": desviacion,
        "decimales": decimales,
        "frecuencia": punto.get("frecuencia"),
        "criterio": punto.get("criterio"),
        "estado": punto.get("estado"),
        "codigo_patron": punto.get("codigo_patron"),
    }


def evaluar_resultado(
    resultado_observado,
    valor_nominal,
    limite_inferior,
    limite_superior,
):
    """
    Evalúa un resultado contra límites absolutos.

    Ejemplo:
    nominal = 0.0200
    límite inferior = 0.0198
    límite superior = 0.0202
    """
    resultado = limpiar_numero(resultado_observado)
    nominal = limpiar_numero(valor_nominal)
    limite_inferior_real = limpiar_numero(limite_inferior)
    limite_superior_real = limpiar_numero(limite_superior)

    error = (
        resultado - nominal
        if resultado is not None and nominal is not None
        else None
    )

    if resultado is None:
        return {
            "resultado": resultado_observado,
            "valor_nominal": nominal,
            "error": error,
            "limite_inferior_real": limite_inferior_real,
            "limite_superior_real": limite_superior_real,
            "cumple": None,
            "estado": "Sin resultado",
            "mensaje": "No se ingresó un resultado válido.",
        }

    if limite_inferior_real is None or limite_superior_real is None:
        return {
            "resultado": resultado,
            "valor_nominal": nominal,
            "error": error,
            "limite_inferior_real": limite_inferior_real,
            "limite_superior_real": limite_superior_real,
            "cumple": None,
            "estado": "Sin límites",
            "mensaje": "El punto no tiene límites configurados.",
        }

    if limite_inferior_real > limite_superior_real:
        limite_inferior_real, limite_superior_real = (
            limite_superior_real,
            limite_inferior_real,
        )

    cumple = limite_inferior_real <= resultado <= limite_superior_real

    return {
        "resultado": resultado,
        "valor_nominal": nominal,
        "error": error,
        "limite_inferior_real": limite_inferior_real,
        "limite_superior_real": limite_superior_real,
        "cumple": cumple,
        "estado": "Cumple" if cumple else "No cumple",
        "mensaje": (
            "Resultado dentro de los límites configurados."
            if cumple
            else "Resultado fuera de los límites configurados."
        ),
    }