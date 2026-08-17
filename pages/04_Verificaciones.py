from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from utils.ui import (
    aplicar_estilo,
    encabezado,
    pie_pagina,
    sidebar_pro,
)
from utils.data import cargar_hoja
from utils.permisos import (
    obtener_equipos_permitidos,
    puede_verificar_equipo,
    obtener_laboratorio_usuario,
    obtener_rol_usuario,
)
from utils.formatos import formatear_numero
from utils.persistencia import generar_id_sesion
from utils.persistencia_supabase import guardar_sesion_supabase
from utils.persistencia_bitacora import registrar_eventos_verificacion
from utils.diagnostico import generar_diagnostico_sesion
from utils.verificacion_engine import (
    obtener_puntos_equipo,
    preparar_punto_para_verificacion,
)

st.set_page_config(
    page_title="Verificaciones - PROVICHECK",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilo()

if not st.session_state.get("autenticado", False):
    st.warning("La sesión no está activa. Ingrese nuevamente desde el Dashboard.")
    st.page_link("app.py", label="🔐 Ir al inicio de sesión")
    st.stop()

sidebar_pro()
encabezado()

st.markdown("## ✅ Motor inteligente de verificación")
st.caption(
    "Registre verificaciones en tiempo real o incorpore resultados históricos "
    "manteniendo la trazabilidad permanente en PROVICHECK."
)

DECIMALES = 4
DIAS_ALERTA_VENCIMIENTO = 30

st.markdown(
    """
    <style>
    /* Valores técnicos de las tarjetas: tamaño uniforme de 12 px */
    .provicheck-tech-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.35rem 0 0.8rem 0;
    }

    .provicheck-tech-box {
        background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
        border: 1px solid #cbd8e8;
        border-top: 3px solid #147a3b;
        border-radius: 10px;
        padding: 0.62rem 0.72rem;
        min-height: 72px;
        box-shadow: 0 3px 10px rgba(15, 39, 71, 0.06);
    }

    .provicheck-tech-label {
        color: #35506f;
        font-size: 11px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.42rem;
    }

    .provicheck-tech-value {
        color: #0f2747;
        font-size: 12px;
        font-weight: 800;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .provicheck-pattern-box {
        border: 1px solid #cbd8e8;
        border-left: 5px solid #147a3b;
        border-radius: 10px;
        background: #f8fbff;
        padding: 0.7rem 0.85rem;
        margin: 0.4rem 0 0.8rem 0;
        color: #0f2747;
        font-size: 12px;
        line-height: 1.45;
    }

    .provicheck-pattern-box.warning {
        border-left-color: #d99a00;
        background: #fffaf0;
    }

    .provicheck-pattern-box.danger {
        border-left-color: #c62828;
        background: #fff5f5;
    }

    .provicheck-pattern-box.neutral {
        border-left-color: #6b7d90;
        background: #f7f8fa;
    }

    .provicheck-pattern-title {
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }

    .provicheck-pattern-status {
        font-size: 12px;
        font-weight: 800;
        margin-top: 0.35rem;
    }

    /* Tarjetas compactas para identificación del equipo */
    .pc-id-card {
        background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
        border: 1px solid #cbd8e8;
        border-top: 3px solid #147a3b;
        border-radius: 11px;
        padding: 0.70rem 0.78rem;
        min-height: 92px;
        box-shadow: 0 3px 10px rgba(15, 39, 71, 0.05);
        overflow: hidden;
    }

    .pc-id-label {
        color: #506784;
        font-size: 11px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.45rem;
    }

    .pc-id-value {
        color: #0f2747;
        font-size: 15px;
        font-weight: 800;
        line-height: 1.22;
        overflow-wrap: anywhere;
        word-break: normal;
    }

    /* El resultado digitado queda con el mismo tamaño visual de 12 px */
    div[data-testid="stNumberInput"] input {
        font-size: 12px !important;
        font-weight: 700 !important;
        color: #0f2747 !important;
    }

    div[data-testid="stNumberInput"] label p {
        font-size: 12px !important;
        font-weight: 600 !important;
    }

    @media (max-width: 900px) {
        .provicheck-tech-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def texto_seguro(valor, por_defecto="No informado"):
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def normalizar_codigo(valor):
    texto = texto_seguro(valor, "")
    if not texto:
        return ""

    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base

    return texto


def convertir_fecha(valor):
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    texto = texto_seguro(valor, "")
    if not texto:
        return None

    formatos = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
    )

    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        return None


def construir_indice_patrones(tabla_patrones):
    indice = {}

    if tabla_patrones.empty or "codigo_patron" not in tabla_patrones.columns:
        return indice

    for _, fila_patron in tabla_patrones.iterrows():
        datos = fila_patron.to_dict()
        codigo = normalizar_codigo(datos.get("codigo_patron"))
        if codigo:
            indice[codigo] = datos

    return indice


def construir_relaciones_equipo_patron(tabla_relaciones):
    relaciones = set()

    columnas_necesarias = {"codigo_equipo", "codigo_patron"}
    if (
        tabla_relaciones.empty
        or not columnas_necesarias.issubset(tabla_relaciones.columns)
    ):
        return relaciones

    for _, fila_relacion in tabla_relaciones.iterrows():
        codigo_equipo_rel = normalizar_codigo(
            fila_relacion.get("codigo_equipo")
        )
        codigo_patron_rel = normalizar_codigo(
            fila_relacion.get("codigo_patron")
        )
        estado_relacion = texto_seguro(
            fila_relacion.get("estado"),
            "Activo",
        ).lower()

        if (
            codigo_equipo_rel
            and codigo_patron_rel
            and estado_relacion not in {"inactivo", "anulado", "retirado"}
        ):
            relaciones.add((codigo_equipo_rel, codigo_patron_rel))

    return relaciones


def evaluar_patron(
    codigo_equipo_actual,
    codigo_patron,
    indice_patrones,
    relaciones_equipo_patron,
    fecha_referencia,
):
    codigo = normalizar_codigo(codigo_patron)

    resultado = {
        "requiere_patron": bool(codigo),
        "codigo": codigo,
        "descripcion": "",
        "marca": "",
        "valor_nominal": None,
        "unidad": "",
        "fecha_vencimiento": None,
        "fecha_vencimiento_texto": "Sin fecha",
        "dias_para_vencer": None,
        "estado": "No aplica",
        "mensaje": "Este punto no tiene patrón asociado.",
        "clase_css": "neutral",
        "icono": "⚪",
        "bloqueado": False,
        "relacion_valida": True,
    }

    if not codigo:
        return resultado

    datos_patron = indice_patrones.get(codigo)

    if datos_patron is None:
        resultado.update(
            {
                "estado": "Sin información",
                "mensaje": (
                    "El código está asignado al punto, pero no fue encontrado "
                    "en Equipos_Patrones. El punto permanece habilitado."
                ),
                "clase_css": "warning",
                "icono": "🟡",
                "relacion_valida": (
                    normalizar_codigo(codigo_equipo_actual),
                    codigo,
                ) in relaciones_equipo_patron,
            }
        )
        return resultado

    fecha_vencimiento = convertir_fecha(
        datos_patron.get("fecha_vencimiento_calibracion")
    )
    estado_maestro = texto_seguro(
        datos_patron.get("estado"),
        "Activo",
    ).lower()

    relacion_valida = (
        normalizar_codigo(codigo_equipo_actual),
        codigo,
    ) in relaciones_equipo_patron

    resultado.update(
        {
            "descripcion": texto_seguro(
                datos_patron.get("descripcion"),
                "Sin descripción",
            ),
            "marca": texto_seguro(
                datos_patron.get("marca"),
                "Sin marca",
            ),
            "valor_nominal": numero_seguro(
                datos_patron.get("valor_nominal_g")
            ),
            "unidad": texto_seguro(datos_patron.get("unidad"), ""),
            "fecha_vencimiento": fecha_vencimiento,
            "fecha_vencimiento_texto": (
                fecha_vencimiento.strftime("%d/%m/%Y")
                if fecha_vencimiento
                else "Sin fecha"
            ),
            "relacion_valida": relacion_valida,
        }
    )

    if estado_maestro in {"inactivo", "anulado", "retirado", "fuera de servicio"}:
        resultado.update(
            {
                "estado": "No disponible",
                "mensaje": (
                    "El patrón está marcado como no disponible en la base maestra. "
                    "Solo este punto queda bloqueado."
                ),
                "clase_css": "danger",
                "icono": "🔴",
                "bloqueado": True,
            }
        )
        return resultado

    if fecha_vencimiento is None:
        resultado.update(
            {
                "estado": "Sin fecha de vencimiento",
                "mensaje": (
                    "No se encontró fecha de vencimiento. "
                    "El punto permanece habilitado con advertencia."
                ),
                "clase_css": "warning",
                "icono": "🟡",
            }
        )
        return resultado

    dias_para_vencer = (fecha_vencimiento - fecha_referencia).days
    resultado["dias_para_vencer"] = dias_para_vencer

    if dias_para_vencer < 0:
        resultado.update(
            {
                "estado": "Vencido",
                "mensaje": (
                    f"El patrón venció hace {abs(dias_para_vencer)} día(s). "
                    "Solo este punto queda bloqueado."
                ),
                "clase_css": "danger",
                "icono": "🔴",
                "bloqueado": True,
            }
        )
    elif dias_para_vencer <= DIAS_ALERTA_VENCIMIENTO:
        resultado.update(
            {
                "estado": "Próximo a vencer",
                "mensaje": (
                    f"El patrón vence en {dias_para_vencer} día(s). "
                    "El punto puede verificarse."
                ),
                "clase_css": "warning",
                "icono": "🟡",
            }
        )
    else:
        resultado.update(
            {
                "estado": "Vigente",
                "mensaje": (
                    f"Patrón vigente. Faltan {dias_para_vencer} día(s) "
                    "para el vencimiento."
                ),
                "clase_css": "",
                "icono": "🟢",
            }
        )

    if not relacion_valida:
        resultado["mensaje"] += (
            " Advertencia: no se encontró una relación activa entre "
            "este equipo y el patrón."
        )
        if not resultado["bloqueado"]:
            resultado["clase_css"] = "warning"
            resultado["icono"] = "🟡"

    return resultado


def mostrar_panel_patron(info_patron, decimales):
    if not info_patron["requiere_patron"]:
        st.markdown(
            """
            <div class="provicheck-pattern-box neutral">
                <div class="provicheck-pattern-title">
                    ⚪ PATRÓN: NO APLICA
                </div>
                Este punto no requiere un patrón metrológico.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    valor_patron = formatear_numero(
        info_patron.get("valor_nominal"),
        decimales,
    )
    unidad_patron = info_patron.get("unidad", "")
    relacion_texto = (
        "Confirmada"
        if info_patron.get("relacion_valida")
        else "No encontrada"
    )

    st.markdown(
        f"""
        <div class="provicheck-pattern-box {info_patron['clase_css']}">
            <div class="provicheck-pattern-title">
                {info_patron['icono']} PATRÓN ASOCIADO ·
                {info_patron['estado'].upper()}
            </div>
            <strong>Código:</strong> {info_patron['codigo']}<br>
            <strong>Descripción:</strong>
            {info_patron.get('descripcion') or 'Sin información'}<br>
            <strong>Marca:</strong>
            {info_patron.get('marca') or 'Sin información'}<br>
            <strong>Valor nominal:</strong>
            {valor_patron} {unidad_patron}<br>
            <strong>Vencimiento:</strong>
            {info_patron['fecha_vencimiento_texto']}<br>
            <strong>Relación equipo–patrón:</strong> {relacion_texto}
            <div class="provicheck-pattern-status">
                {info_patron['mensaje']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_valores_tecnicos(
    valor_nominal,
    limite_inferior,
    limite_superior,
    unidad,
    decimales,
):
    patron_texto = formatear_numero(valor_nominal, decimales)
    inferior_texto = formatear_numero(limite_inferior, decimales)
    superior_texto = formatear_numero(limite_superior, decimales)

    st.markdown(
        f"""
        <div class="provicheck-tech-grid">
            <div class="provicheck-tech-box">
                <div class="provicheck-tech-label">Patrón</div>
                <div class="provicheck-tech-value">
                    {patron_texto} {unidad}
                </div>
            </div>
            <div class="provicheck-tech-box">
                <div class="provicheck-tech-label">Límite inferior</div>
                <div class="provicheck-tech-value">
                    {inferior_texto} {unidad}
                </div>
            </div>
            <div class="provicheck-tech-box">
                <div class="provicheck-tech-label">Límite superior</div>
                <div class="provicheck-tech-value">
                    {superior_texto} {unidad}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def numero_seguro(valor):
    try:
        if valor is None or str(valor).strip() == "":
            return None
        numero = float(valor)
        if numero != numero:
            return None
        return numero
    except (TypeError, ValueError):
        return None


def obtener_limites_reales(fila_original, punto_preparado):
    nominal = numero_seguro(
        fila_original.get(
            "valor_nominal_g",
            fila_original.get(
                "valor_nominal",
                punto_preparado.get("valor_nominal"),
            ),
        )
    )

    limite_inferior = numero_seguro(
        fila_original.get(
            "limite_inferior_g",
            fila_original.get("limite_inferior"),
        )
    )
    limite_superior = numero_seguro(
        fila_original.get(
            "limite_superior_g",
            fila_original.get("limite_superior"),
        )
    )

    desviacion = numero_seguro(
        fila_original.get(
            "desviacion_aceptada_g",
            fila_original.get("desviacion_aceptada"),
        )
    )

    if nominal is not None and desviacion is not None:
        if limite_inferior is None:
            limite_inferior = nominal - desviacion
        if limite_superior is None:
            limite_superior = nominal + desviacion

    return nominal, limite_inferior, limite_superior


def combinar_fecha_hora(fecha_seleccionada, hora_seleccionada):
    return datetime.combine(fecha_seleccionada, hora_seleccionada)


OPCIONES_OBSERVACION = [
    "Sin novedades",
    "Patrón en calibración",
    "Patrón no disponible",
    "Patrón vencido",
    "Equipo inestable",
    "Equipo fuera de servicio",
    "Mantenimiento",
    "No aplica",
    "Otro",
]

equipos = cargar_hoja("Equipos")
puntos = cargar_hoja("Puntos_Verificacion")
patrones = cargar_hoja("Equipos_Patrones")
relaciones_equipo_patron = cargar_hoja("Relacion_Equipo_Patron")

if equipos.empty:
    st.error("No se encontró la hoja Equipos.")
    st.stop()

if puntos.empty:
    st.error("No se encontró la hoja Puntos_Verificacion.")
    st.stop()

equipos = equipos.copy()
equipos.columns = [str(columna).strip() for columna in equipos.columns]

# Control de autorización:
# - Administrador/Líder: todos los equipos.
# - Analista: únicamente equipos de su laboratorio asignado.
equipos = obtener_equipos_permitidos(equipos)

if equipos.empty:
    laboratorio_usuario = obtener_laboratorio_usuario()
    st.error(
        "No tiene equipos autorizados para realizar verificaciones. "
        f"Laboratorio asignado: {laboratorio_usuario or 'No informado'}."
    )
    st.stop()

puntos = puntos.copy()
puntos.columns = [str(columna).strip() for columna in puntos.columns]

if "codigo_equipo" in equipos.columns:
    equipos["codigo_equipo"] = equipos["codigo_equipo"].apply(normalizar_codigo)

if "codigo_equipo" in puntos.columns:
    puntos["codigo_equipo"] = puntos["codigo_equipo"].apply(normalizar_codigo)

patrones = patrones.copy()
patrones.columns = [str(columna).strip() for columna in patrones.columns]

relaciones_equipo_patron = relaciones_equipo_patron.copy()
relaciones_equipo_patron.columns = [
    str(columna).strip()
    for columna in relaciones_equipo_patron.columns
]

indice_patrones = construir_indice_patrones(patrones)
relaciones_activas = construir_relaciones_equipo_patron(
    relaciones_equipo_patron
)

alias_columnas = {
    "limite_inferior_g": "limite_inferior",
    "valor_nominal_g": "valor_nominal",
    "limite_superior_g": "limite_superior",
    "desviacion_aceptada_g": "desviacion_aceptada",
}

for columna_origen, columna_destino in alias_columnas.items():
    if columna_origen in puntos.columns and columna_destino not in puntos.columns:
        puntos[columna_destino] = puntos[columna_origen]

columnas_requeridas = {"codigo_equipo", "nombre_equipo"}
faltantes = columnas_requeridas.difference(equipos.columns)

if faltantes:
    st.error(
        "La hoja Equipos no contiene las columnas requeridas: "
        + ", ".join(sorted(faltantes))
    )
    st.stop()

equipos["descripcion"] = (
    equipos["codigo_equipo"].apply(normalizar_codigo)
    + " · "
    + equipos["nombre_equipo"].astype(str).str.strip()
)

rol_usuario = obtener_rol_usuario()
laboratorio_usuario = obtener_laboratorio_usuario()

with st.container(border=True):
    st.markdown("### 🔐 Alcance de autorización")
    if rol_usuario in {"Administrador", "Líder"}:
        st.success(
            f"{rol_usuario}: puede realizar verificaciones sobre todos los equipos."
        )
    else:
        st.info(
            "Analista autorizado únicamente para equipos del laboratorio: "
            f"**{laboratorio_usuario or 'No informado'}**."
        )

st.markdown("### 1. Modo de captura")

with st.container(border=True):
    modo_captura = st.radio(
        "Seleccione cómo desea registrar la verificación",
        ["Tiempo real", "Carga histórica"],
        horizontal=True,
        help=(
            "Tiempo real usa la fecha y hora actual. "
            "Carga histórica permite registrar verificaciones realizadas anteriormente."
        ),
    )

    ahora = datetime.now(ZoneInfo("America/Bogota"))

    if modo_captura == "Tiempo real":
        fecha_registro = ahora.date()
        hora_registro = ahora.time().replace(microsecond=0)
        responsable_registro = str(
            st.session_state.get(
                "nombre_usuario",
                st.session_state.get("usuario", ""),
            )
            or ""
        ).strip()

        c_fecha, c_hora, c_resp = st.columns([1, 1, 2])
        c_fecha.metric("Fecha del registro", fecha_registro.strftime("%d/%m/%Y"))
        c_hora.metric("Hora del registro", hora_registro.strftime("%H:%M:%S"))

        with c_resp:
            responsable_registro = st.text_input(
                "Responsable",
                value=responsable_registro,
                placeholder="Nombre del responsable",
                key="responsable_tiempo_real",
            )

        st.info("La sesión se guardará con la fecha y hora actuales.")

    else:
        c_fecha, c_hora, c_resp = st.columns([1, 1, 2])

        with c_fecha:
            fecha_registro = st.date_input(
                "Fecha de la verificación",
                value=date(ahora.year, 1, 1),
                max_value=ahora.date(),
                format="DD/MM/YYYY",
                key="fecha_historica",
            )

        with c_hora:
            hora_registro = st.time_input(
                "Hora de la verificación",
                value=time(8, 0),
                step=60,
                key="hora_historica",
            )

        with c_resp:
            responsable_registro = st.text_input(
                "Responsable de la verificación",
                placeholder="Nombre del analista que realizó la verificación",
                key="responsable_historico",
            )

        st.warning(
            "Modo histórico activo. Verifique cuidadosamente la fecha, la hora "
            "y el responsable antes de guardar."
        )

fecha_hora_registro = combinar_fecha_hora(fecha_registro, hora_registro)

st.markdown("### 2. Selección del equipo")

col_equipo, col_vista = st.columns([3, 1])

with col_equipo:
    equipo_sel = st.selectbox(
        "Seleccione el equipo que desea verificar",
        options=equipos["descripcion"].tolist(),
        index=None,
        placeholder="Seleccione un equipo...",
    )

with col_vista:
    tarjetas_por_fila = st.selectbox(
        "Tarjetas por fila",
        [2, 1, 3],
        index=0,
        key="tarjetas_por_fila_verificacion",
    )

if not equipo_sel:
    st.info(
        "Seleccione un equipo para cargar su identificación "
        "y sus puntos de verificación."
    )
    pie_pagina()
    st.stop()

# ÚNICA FUENTE DE VERDAD:
# el valor actual devuelto por el selector.
codigo_equipo = normalizar_codigo(
    str(equipo_sel).split(" · ", 1)[0]
)

coincidencias = equipos[
    equipos["codigo_equipo"]
    .apply(normalizar_codigo)
    .eq(codigo_equipo)
]

if coincidencias.empty:
    st.error(
        "No fue posible localizar la información del equipo seleccionado."
    )
    st.stop()

equipo_info = coincidencias.iloc[0].to_dict()

# Los puntos se calculan desde el mismo código en este mismo render.
puntos_equipo = puntos[
    puntos["codigo_equipo"]
    .apply(normalizar_codigo)
    .eq(codigo_equipo)
].copy()

st.markdown("### 3. Identificación del equipo")

analista_sesion = str(
    st.session_state.get(
        "nombre_usuario",
        st.session_state.get("usuario", "Usuario no identificado"),
    )
    or "Usuario no identificado"
).strip()

identificacion_tarjetas = [
    ("Código", equipo_info.get("codigo_equipo", "")),
    ("Estado", equipo_info.get("estado", "Sin estado")),
    ("Laboratorio", equipo_info.get("laboratorio", "Sin laboratorio")),
    ("Analista", analista_sesion),
]

columnas_identificacion = st.columns(4)

for columna_identificacion, (etiqueta, valor) in zip(
    columnas_identificacion,
    identificacion_tarjetas,
):
    with columna_identificacion:
        st.markdown(
            f"""
            <div class="pc-id-card">
                <div class="pc-id-label">{escape(str(etiqueta))}</div>
                <div class="pc-id-value">{escape(str(valor))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with st.container(border=True):
    col_a, col_b, col_c = st.columns(3)
    col_a.write(
        f"**Equipo:** {equipo_info.get('nombre_equipo', 'Sin nombre')}"
    )
    col_b.write(
        f"**Marca / Modelo:** "
        f"{equipo_info.get('marca', 'Sin marca')} · "
        f"{equipo_info.get('modelo', 'Sin modelo')}"
    )
    col_c.write(
        f"**Ubicación:** {equipo_info.get('ubicacion', 'Sin ubicación')}"
    )

st.divider()

if puntos_equipo.empty:
    st.warning("Este equipo no tiene puntos de verificación configurados.")
    pie_pagina()
    st.stop()

st.markdown("### 4. Puntos de verificación")
st.caption(
    f"El equipo tiene {len(puntos_equipo)} punto(s) configurado(s). "
    "Cada resultado se evalúa automáticamente frente a sus límites."
)

registros = []
columnas = st.columns(tarjetas_por_fila)

for i, (_, fila) in enumerate(puntos_equipo.iterrows()):
    fila_original = fila.to_dict()
    punto = preparar_punto_para_verificacion(fila_original)
    unidad = str(punto.get("unidad", "") or "").strip()
    id_punto = punto.get("id_punto", i)
    nombre_punto = punto.get("punto_verificacion", f"Punto {i + 1}")
    nombre_chequeo = punto.get("nombre_chequeo", "Chequeo sin nombre")

    decimales_punto = punto.get(
        "decimales",
        fila_original.get(
            "decimales",
            fila_original.get("numero_decimales", DECIMALES),
        ),
    )
    try:
        decimales_punto = int(float(decimales_punto))
    except (TypeError, ValueError):
        decimales_punto = DECIMALES

    decimales_punto = max(0, min(decimales_punto, 8))

    with columnas[i % tarjetas_por_fila]:
        with st.container(border=True):
            st.markdown(
                f'''
                <div class="verification-card-title">
                    <span class="verification-card-badge">📌</span>
                    <span>{nombre_punto} {unidad}</span>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.caption(nombre_chequeo)

            (
                valor_nominal,
                limite_inferior,
                limite_superior,
            ) = obtener_limites_reales(fila_original, punto)

            codigo_patron_punto = fila_original.get("codigo_patron", "")
            info_patron = evaluar_patron(
                codigo_equipo,
                codigo_patron_punto,
                indice_patrones,
                relaciones_activas,
                fecha_registro,
            )

            mostrar_panel_patron(info_patron, decimales_punto)
            mostrar_valores_tecnicos(
                valor_nominal,
                limite_inferior,
                limite_superior,
                unidad,
                decimales_punto,
            )

            resultado_capturado = st.number_input(
                "Resultado observado",
                value=None,
                key=f"resultado_{codigo_equipo}_{id_punto}",
                format=f"%.{decimales_punto}f",
                disabled=info_patron["bloqueado"],
                help=(
                    "Este campo está bloqueado únicamente para este punto "
                    "porque el patrón asociado no se encuentra disponible."
                    if info_patron["bloqueado"]
                    else "Ingrese la lectura observada para este punto."
                ),
            )

            if info_patron["bloqueado"]:
                resultado = None
                observacion_tipo = (
                    "Patrón vencido"
                    if info_patron["estado"] == "Vencido"
                    else "Patrón no disponible"
                )
                st.selectbox(
                    "Observación",
                    [observacion_tipo],
                    key=f"obs_tipo_{codigo_equipo}_{id_punto}",
                    disabled=True,
                )
            else:
                resultado = resultado_capturado
                observacion_tipo = st.selectbox(
                    "Observación",
                    OPCIONES_OBSERVACION,
                    key=f"obs_tipo_{codigo_equipo}_{id_punto}",
                )

            observacion_texto = ""
            if observacion_tipo == "Otro":
                observacion_texto = st.text_area(
                    "Detalle de la observación",
                    key=f"obs_txt_{codigo_equipo}_{id_punto}",
                    placeholder="Describa la novedad encontrada.",
                )

            if info_patron["bloqueado"]:
                observacion_final = (
                    f"{observacion_tipo}. Patrón "
                    f"{info_patron.get('codigo') or 'sin código'}; "
                    f"estado: {info_patron.get('estado')}; "
                    f"vencimiento: "
                    f"{info_patron.get('fecha_vencimiento_texto')}. "
                    f"{info_patron.get('mensaje')}"
                )
            else:
                observacion_final = (
                    observacion_texto.strip()
                    if observacion_tipo == "Otro"
                    else observacion_tipo
                )

            resultado_num = numero_seguro(resultado)
            error_calculado = (
                resultado_num - valor_nominal
                if resultado_num is not None and valor_nominal is not None
                else None
            )

            if (
                resultado_num is not None
                and limite_inferior is not None
                and limite_superior is not None
            ):
                cumple_calculado = (
                    limite_inferior <= resultado_num <= limite_superior
                )
            else:
                cumple_calculado = None

            evaluacion = {
                "error": error_calculado,
                "limite_inferior_real": limite_inferior,
                "limite_superior_real": limite_superior,
                "cumple": cumple_calculado,
            }

            st.write(
                f"**Error calculado:** "
                f"{formatear_numero(evaluacion.get('error'), decimales_punto)} "
                f"{unidad}"
            )
            st.write(
                f"**Intervalo real:** "
                f"{formatear_numero(evaluacion.get('limite_inferior_real'), decimales_punto)} "
                f"a "
                f"{formatear_numero(evaluacion.get('limite_superior_real'), decimales_punto)} "
                f"{unidad}"
            )

            if info_patron["bloqueado"]:
                estado_punto = "No evaluado"
                st.error(
                    "🔴 NO EVALUADO · El patrón asociado impide evaluar "
                    "únicamente este punto"
                )
            elif observacion_tipo != "Sin novedades":
                estado_punto = "No evaluado"
                st.warning("🟡 NO EVALUADO · Existe una novedad registrada")
            elif evaluacion.get("cumple") is True:
                estado_punto = "Cumple"
                st.success("🟢 CUMPLE")
            elif evaluacion.get("cumple") is False:
                estado_punto = "No cumple"
                st.error("🔴 NO CUMPLE")
            else:
                estado_punto = "No evaluado"
                st.warning("🟡 SIN EVALUACIÓN O SIN LÍMITES")

            registros.append(
                {
                    "codigo_equipo": codigo_equipo,
                    "punto": nombre_punto,
                    "nombre_chequeo": nombre_chequeo,
                    "valor_nominal": valor_nominal,
                    "resultado": resultado,
                    "error": evaluacion.get("error"),
                    "limite_inferior": evaluacion.get(
                        "limite_inferior_real"
                    ),
                    "limite_superior": evaluacion.get(
                        "limite_superior_real"
                    ),
                    "estado_punto": estado_punto,
                    "observacion": observacion_final,
                    "codigo_patron": info_patron.get("codigo", ""),
                    "estado_patron": info_patron.get("estado", ""),
                    "fecha_vencimiento_patron": (
                        info_patron["fecha_vencimiento"].isoformat()
                        if info_patron.get("fecha_vencimiento")
                        else ""
                    ),
                    "patron_bloqueado": info_patron.get("bloqueado", False),
                }
            )

st.divider()
st.markdown("### 5. Resumen de la sesión")

total = len(registros)
cumplen = sum(
    1 for registro in registros
    if registro["estado_punto"] == "Cumple"
)
no_cumplen = sum(
    1 for registro in registros
    if registro["estado_punto"] == "No cumple"
)
no_evaluados = sum(
    1 for registro in registros
    if registro["estado_punto"] == "No evaluado"
)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Puntos configurados", total)
r2.metric("Cumplen", cumplen)
r3.metric("No cumplen", no_cumplen)
r4.metric("No evaluados", no_evaluados)

if no_cumplen > 0:
    estado_sesion = "No conforme"
elif no_evaluados > 0:
    estado_sesion = "Incompleta"
else:
    estado_sesion = "Conforme"

diagnostico = generar_diagnostico_sesion(
    estado_sesion,
    total,
    cumplen,
    no_cumplen,
    no_evaluados,
)

if estado_sesion == "Conforme":
    st.success("### 🟢 Estado de la sesión: CONFORME")
elif estado_sesion == "No conforme":
    st.error("### 🔴 Estado de la sesión: NO CONFORME")
else:
    st.warning("### 🟡 Estado de la sesión: INCOMPLETA")

with st.container(border=True):
    st.markdown("### 🧠 Diagnóstico automático")
    st.write(diagnostico)

st.markdown("### 6. Guardar verificación")

with st.container(border=True):
    st.write(f"**Modo:** {modo_captura}")
    st.write(
        f"**Fecha y hora que se guardarán:** "
        f"{fecha_hora_registro.strftime('%d/%m/%Y %H:%M:%S')}"
    )
    st.write(
        f"**Responsable:** "
        f"{responsable_registro.strip() or 'No informado'}"
    )

confirmar = st.checkbox(
    "Confirmo que revisé los resultados, la fecha, la hora y las observaciones."
)

responsable_valido = bool(responsable_registro.strip())

if not responsable_valido:
    st.warning("Debe ingresar el responsable antes de guardar la verificación.")

guardar = st.button(
    "💾 Guardar verificación en PROVICHECK",
    width="stretch",
    disabled=not (confirmar and responsable_valido),
)

if guardar:
    # Segunda validación de seguridad antes de persistir.
    # Evita guardar un equipo no autorizado aunque se manipule la interfaz.
    autorizado, motivo = puede_verificar_equipo(equipo_info)

    if not autorizado:
        st.error(f"⛔ Verificación bloqueada. {motivo}")
        st.stop()

    id_sesion = generar_id_sesion(codigo_equipo)

    sesion = {
        "id_sesion": id_sesion,
        "codigo_equipo": codigo_equipo,
        "nombre_equipo": equipo_info.get("nombre_equipo", ""),
        "laboratorio": equipo_info.get("laboratorio", ""),
        "fecha": fecha_hora_registro.date().isoformat(),
        "hora": fecha_hora_registro.time().strftime("%H:%M:%S"),
        "responsable": responsable_registro.strip(),
        "estado": estado_sesion,
        "total_puntos": total,
        "puntos_cumplen": cumplen,
        "puntos_no_cumplen": no_cumplen,
        "puntos_no_evaluados": no_evaluados,
    }

    ok, mensaje = guardar_sesion_supabase(sesion, registros)

    if ok:
        ok_bitacora, mensaje_bitacora = registrar_eventos_verificacion(
            sesion,
            registros,
        )

        st.success(f"✅ {mensaje}")

        if ok_bitacora:
            st.info(f"📖 {mensaje_bitacora}")
        else:
            st.warning(
                "La verificación quedó guardada correctamente, "
                "pero no fue posible actualizar la bitácora. "
                f"Detalle: {mensaje_bitacora}"
            )

        with st.container(border=True):
            st.markdown("## ✅ Sesión finalizada")
            st.write(f"**Sesión:** {id_sesion}")
            st.write(
                f"**Equipo:** {codigo_equipo} · "
                f"{equipo_info.get('nombre_equipo', '')}"
            )
            st.write(f"**Modo:** {modo_captura}")
            st.write(f"**Fecha:** {sesion['fecha']} {sesion['hora']}")
            st.write(f"**Responsable:** {sesion['responsable']}")
            st.write(f"**Estado general:** {estado_sesion}")

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Puntos", total)
            f2.metric("Cumplen", cumplen)
            f3.metric("No cumplen", no_cumplen)
            f4.metric("No evaluados", no_evaluados)

            st.markdown("### 🧠 Diagnóstico")
            st.write(diagnostico)
    else:
        st.error(mensaje)

pie_pagina()