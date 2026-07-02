import streamlit as st

from utils.formatos import formatear_numero


def mostrar_card_verificacion(punto, evaluacion, resultado_key, decimales=4):
    cumple = evaluacion.get("cumple")
    unidad = punto.get("unidad", "")

    if cumple is True:
        color_borde = "#22C55E"
        color_fondo = "#0F2F1F"
        estado = "🟢 CUMPLE"
    elif cumple is False:
        color_borde = "#EF4444"
        color_fondo = "#33171A"
        estado = "🔴 NO CUMPLE"
    else:
        color_borde = "#F59E0B"
        color_fondo = "#2F2410"
        estado = "🟡 SIN EVALUACIÓN"

    st.markdown(
        f"""
        <div style="
            border: 2px solid {color_borde};
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 12px;
            background-color: {color_fondo};
            box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;">📌 {punto.get("punto_verificacion", "")} {unidad}</h3>
                <h4 style="margin:0;">{estado}</h4>
            </div>
            <p style="margin-top:8px;"><b>Chequeo:</b> {punto.get("nombre_chequeo", "")}</p>

            <hr style="border: 0.5px solid #334155;">

            <p><b>Valor nominal:</b> {formatear_numero(punto.get("valor_nominal"), decimales)} {unidad}</p>
            <p><b>Tolerancia inferior:</b> {formatear_numero(punto.get("limite_inferior"), decimales)} {unidad}</p>
            <p><b>Tolerancia superior:</b> {formatear_numero(punto.get("limite_superior"), decimales)} {unidad}</p>

            <hr style="border: 0.5px solid #334155;">

            <p><b>Resultado observado:</b> {formatear_numero(evaluacion.get("resultado"), decimales)} {unidad}</p>
            <p><b>Error:</b> {formatear_numero(evaluacion.get("error"), decimales)} {unidad}</p>
            <p><b>Límite inferior real:</b> {formatear_numero(evaluacion.get("limite_inferior_real"), decimales)} {unidad}</p>
            <p><b>Límite superior real:</b> {formatear_numero(evaluacion.get("limite_superior_real"), decimales)} {unidad}</p>

            <p style="margin-top:10px;"><b>Evaluación:</b> {evaluacion.get("mensaje", "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.number_input(
        "Resultado observado",
        key=resultado_key,
        format=f"%.{decimales}f",
    )