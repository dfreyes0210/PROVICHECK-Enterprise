import streamlit as st

from utils.formatos import formatear_numero


def mostrar_card_verificacion(punto, evaluacion, decimales=4):
    cumple = evaluacion.get("cumple")

    if cumple is True:
        color_borde = "#22C55E"
        estado = "🟢 CUMPLE"
    elif cumple is False:
        color_borde = "#EF4444"
        estado = "🔴 NO CUMPLE"
    else:
        color_borde = "#F59E0B"
        estado = "🟡 SIN EVALUACIÓN"

    unidad = punto.get("unidad", "")

    st.markdown(
        f"""
        <div style="
            border: 2px solid {color_borde};
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 18px;
            background-color: #111827;
            box-shadow: 0 4px 14px rgba(0,0,0,0.20);
        ">
            <h4 style="margin-top:0;">📌 {punto.get("punto_verificacion", "")}</h4>
            <p><b>Chequeo:</b> {punto.get("nombre_chequeo", "")}</p>
            <p><b>Valor nominal:</b> {formatear_numero(punto.get("valor_nominal"), decimales)} {unidad}</p>
            <p><b>Tolerancia inferior:</b> {formatear_numero(punto.get("limite_inferior"), decimales)} {unidad}</p>
            <p><b>Tolerancia superior:</b> {formatear_numero(punto.get("limite_superior"), decimales)} {unidad}</p>
            <hr>
            <p><b>Resultado observado:</b> {formatear_numero(evaluacion.get("resultado"), decimales)} {unidad}</p>
            <p><b>Error:</b> {formatear_numero(evaluacion.get("error"), decimales)} {unidad}</p>
            <p><b>Límite inferior real:</b> {formatear_numero(evaluacion.get("limite_inferior_real"), decimales)} {unidad}</p>
            <p><b>Límite superior real:</b> {formatear_numero(evaluacion.get("limite_superior_real"), decimales)} {unidad}</p>
            <h4>{estado}</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )