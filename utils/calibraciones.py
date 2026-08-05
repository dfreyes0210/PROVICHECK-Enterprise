from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from database import get_connection
from utils.data import cargar_hoja
from utils.persistencia_bitacora import registrar_evento_bitacora
from utils.supabase_client import obtener_cliente_supabase


ZONA_COLOMBIA = ZoneInfo("America/Bogota")

ESTADOS_RESULTADO = [
    "Aprobada",
    "Aprobada con observaciones",
    "Condicionada",
    "Rechazada",
]

TIPOS_CALIBRACION = [
    "Externa",
    "Interna",
]


def _ahora_colombia() -> datetime:
    return datetime.now(ZONA_COLOMBIA)


def _fecha_iso(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    return texto or None


def _texto_seguro(valor: Any, por_defecto: str = "") -> str:
    if valor is None:
        return por_defecto
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto
    return texto


def _normalizar_codigo(valor: Any) -> str:
    texto = _texto_seguro(valor)
    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base
    return texto


def _obtener_identidad_equipo(codigo_equipo: str) -> tuple[str, str]:
    try:
        equipos = cargar_hoja("Equipos")
        if equipos.empty or "codigo_equipo" not in equipos.columns:
            return "", ""

        codigo = _normalizar_codigo(codigo_equipo)
        coincidencias = equipos[
            equipos["codigo_equipo"].apply(_normalizar_codigo).eq(codigo)
        ]
        if coincidencias.empty:
            return "", ""

        fila = coincidencias.iloc[0]
        return (
            _texto_seguro(fila.get("nombre_equipo")),
            _texto_seguro(fila.get("laboratorio")),
        )
    except Exception:
        return "", ""


def calcular_estado_calibracion(
    fecha_proxima_calibracion: Any,
    dias_alerta: int = 30,
) -> str:
    fecha_txt = _fecha_iso(fecha_proxima_calibracion)
    if not fecha_txt:
        return "Sin vencimiento"

    try:
        fecha_limite = date.fromisoformat(fecha_txt)
    except ValueError:
        return "Fecha inválida"

    dias_restantes = (fecha_limite - date.today()).days
    if dias_restantes < 0:
        return "Vencida"
    if dias_restantes <= int(dias_alerta):
        return "Próxima a vencer"
    return "Vigente"


def dias_para_vencimiento(fecha_proxima_calibracion: Any) -> int | None:
    fecha_txt = _fecha_iso(fecha_proxima_calibracion)
    if not fecha_txt:
        return None
    try:
        fecha_limite = date.fromisoformat(fecha_txt)
    except ValueError:
        return None
    return (fecha_limite - date.today()).days


def _consultar_documentos_sqlite() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id AS documento_id,
                nombre_archivo AS documento_nombre,
                ruta_archivo AS documento_ruta,
                mime_type AS documento_mime
            FROM documentos_equipo
            """,
            conn,
        )
    except Exception:
        return pd.DataFrame(
            columns=[
                "documento_id",
                "documento_nombre",
                "documento_ruta",
                "documento_mime",
            ]
        )
    finally:
        conn.close()


def registrar_calibracion(
    codigo_equipo: str,
    tipo_calibracion: str,
    numero_certificado: str,
    laboratorio_calibracion: str,
    laboratorio_acreditado: bool,
    organismo_acreditador: str,
    alcance_acreditado: str,
    responsable: str,
    fecha_calibracion: Any,
    fecha_proxima_calibracion: Any,
    frecuencia_meses: int | None,
    resultado: str,
    incertidumbre: str,
    factor_cobertura: str,
    patron_utilizado: str,
    codigo_patron: str,
    certificado_patron: str,
    vencimiento_patron: Any,
    documento_id: int | None,
    observaciones: str,
    usuario_registro: str = "",
) -> int:
    codigo = _normalizar_codigo(codigo_equipo)
    tipo = _texto_seguro(tipo_calibracion)
    resultado_txt = _texto_seguro(resultado)
    fecha_cal = _fecha_iso(fecha_calibracion)
    fecha_proxima = _fecha_iso(fecha_proxima_calibracion)

    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")
    if tipo not in TIPOS_CALIBRACION:
        raise ValueError("El tipo de calibración no es válido.")
    if not fecha_cal:
        raise ValueError("Debe indicar la fecha de calibración.")
    if resultado_txt not in ESTADOS_RESULTADO:
        raise ValueError("El resultado de la calibración no es válido.")
    if fecha_proxima and fecha_proxima < fecha_cal:
        raise ValueError(
            "La próxima calibración no puede ser anterior "
            "a la fecha de calibración."
        )

    ahora = _ahora_colombia()
    estado = calcular_estado_calibracion(fecha_proxima)

    registro = {
        "codigo_equipo": codigo,
        "tipo_calibracion": tipo,
        "numero_certificado": _texto_seguro(numero_certificado),
        "laboratorio_calibracion": _texto_seguro(laboratorio_calibracion),
        "laboratorio_acreditado": bool(laboratorio_acreditado),
        "organismo_acreditador": _texto_seguro(organismo_acreditador),
        "alcance_acreditado": _texto_seguro(alcance_acreditado),
        "responsable": _texto_seguro(responsable),
        "fecha_calibracion": fecha_cal,
        "fecha_proxima_calibracion": fecha_proxima,
        "frecuencia_meses": (
            int(frecuencia_meses)
            if frecuencia_meses not in (None, "", 0)
            else None
        ),
        "resultado": resultado_txt,
        "incertidumbre": _texto_seguro(incertidumbre),
        "factor_cobertura": _texto_seguro(factor_cobertura),
        "patron_utilizado": _texto_seguro(patron_utilizado),
        "codigo_patron": _texto_seguro(codigo_patron),
        "certificado_patron": _texto_seguro(certificado_patron),
        "vencimiento_patron": _fecha_iso(vencimiento_patron),
        "documento_id": int(documento_id) if documento_id else None,
        "observaciones": _texto_seguro(observaciones),
        "estado": estado,
        "usuario_registro": _texto_seguro(usuario_registro),
        "activo": True,
        "fecha_registro": ahora.date().isoformat(),
        "hora_registro": ahora.strftime("%H:%M:%S"),
    }

    try:
        cliente = obtener_cliente_supabase()
        respuesta = cliente.table("calibraciones").insert(registro).execute()
    except Exception as exc:
        raise RuntimeError(
            "No fue posible guardar la calibración en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []
    if not datos:
        raise RuntimeError(
            "Supabase no confirmó el registro de la calibración."
        )

    calibracion_id = int(datos[0]["id"])
    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(codigo)

    if resultado_txt == "Rechazada":
        estado_bitacora = "Error"
    elif resultado_txt in {"Condicionada", "Aprobada con observaciones"}:
        estado_bitacora = "Advertencia"
    else:
        estado_bitacora = "Información"

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio_equipo,
        categoria="Calibración",
        evento="Calibración registrada",
        descripcion=(
            f"Tipo: {tipo}. "
            f"Certificado: "
            f"{_texto_seguro(numero_certificado, 'Sin certificado')}. "
            f"Laboratorio ejecutor: "
            f"{_texto_seguro(laboratorio_calibracion, 'No informado')}. "
            f"Resultado: {resultado_txt}. "
            f"Estado de vigencia: {estado}. "
            f"Fecha de calibración: {fecha_cal}. "
            f"Próxima calibración: "
            f"{fecha_proxima or 'No registrada'}."
        ),
        usuario=_texto_seguro(usuario_registro or responsable),
        estado=estado_bitacora,
        origen="Automático",
        id_referencia=f"CAL-{calibracion_id}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "La calibración quedó guardada en Supabase, pero no fue "
            "posible registrar su evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return calibracion_id


def listar_calibraciones(
    codigo_equipo: str | None = None,
    incluir_inactivas: bool = False,
) -> pd.DataFrame:
    actualizar_estados_calibraciones(codigo_equipo)

    try:
        cliente = obtener_cliente_supabase()
        consulta = cliente.table("calibraciones").select("*")

        if codigo_equipo not in (None, ""):
            consulta = consulta.eq(
                "codigo_equipo",
                _normalizar_codigo(codigo_equipo),
            )

        if not incluir_inactivas:
            consulta = consulta.eq("activo", True)

        respuesta = (
            consulta.order("fecha_calibracion", desc=True)
            .order("id", desc=True)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar las calibraciones en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []
    if not datos:
        return pd.DataFrame()

    calibraciones = pd.DataFrame(datos)
    documentos = _consultar_documentos_sqlite()

    if not documentos.empty and "documento_id" in calibraciones.columns:
        calibraciones = calibraciones.merge(
            documentos,
            how="left",
            on="documento_id",
        )

    return calibraciones


def actualizar_estados_calibraciones(
    codigo_equipo: str | None = None,
) -> int:
    try:
        cliente = obtener_cliente_supabase()
        consulta = (
            cliente.table("calibraciones")
            .select("id,fecha_proxima_calibracion,estado")
            .eq("activo", True)
        )

        if codigo_equipo not in (None, ""):
            consulta = consulta.eq(
                "codigo_equipo",
                _normalizar_codigo(codigo_equipo),
            )

        respuesta = consulta.execute()
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar los estados de calibración. "
            f"Detalle: {exc}"
        ) from exc

    filas = respuesta.data or []
    actualizadas = 0

    for fila in filas:
        nuevo_estado = calcular_estado_calibracion(
            fila.get("fecha_proxima_calibracion")
        )
        if fila.get("estado") == nuevo_estado:
            continue

        try:
            (
                cliente.table("calibraciones")
                .update({"estado": nuevo_estado})
                .eq("id", int(fila["id"]))
                .execute()
            )
            actualizadas += 1
        except Exception as exc:
            raise RuntimeError(
                "No fue posible actualizar el estado de una calibración. "
                f"Detalle: {exc}"
            ) from exc

    return actualizadas


def eliminar_calibracion(
    calibracion_id: int,
    usuario: str = "",
) -> bool:
    cliente = obtener_cliente_supabase()

    try:
        respuesta = (
            cliente.table("calibraciones")
            .select(
                "id,codigo_equipo,tipo_calibracion,"
                "numero_certificado,activo"
            )
            .eq("id", int(calibracion_id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar la calibración. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []
    if not datos:
        raise ValueError("La calibración no existe.")

    fila = datos[0]
    if not bool(fila.get("activo", True)):
        return True

    try:
        (
            cliente.table("calibraciones")
            .update({"activo": False})
            .eq("id", int(calibracion_id))
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible desactivar la calibración en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    ahora = _ahora_colombia()
    codigo = _normalizar_codigo(fila.get("codigo_equipo"))
    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(codigo)

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio_equipo,
        categoria="Calibración",
        evento="Calibración eliminada",
        descripcion=(
            f"Tipo: {fila.get('tipo_calibracion')}. "
            f"Certificado: "
            f"{fila.get('numero_certificado') or 'Sin certificado'}. "
            "Registro desactivado lógicamente en PROVICHECK."
        ),
        usuario=_texto_seguro(usuario),
        estado="Acción administrativa",
        origen="Manual",
        id_referencia=f"CAL-{int(calibracion_id)}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "La calibración fue desactivada en Supabase, pero no fue "
            "posible registrar el evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return True


def resumen_calibraciones(
    codigo_equipo: str | None = None,
) -> dict[str, int | None]:
    calibraciones = listar_calibraciones(codigo_equipo)

    if calibraciones.empty:
        return {
            "total": 0,
            "vigentes": 0,
            "proximas": 0,
            "vencidas": 0,
            "sin_vencimiento": 0,
            "dias_restantes": None,
        }

    dias = calibraciones["fecha_proxima_calibracion"].apply(
        dias_para_vencimiento
    )
    dias_validos = [
        int(valor)
        for valor in dias.tolist()
        if valor is not None and int(valor) >= 0
    ]

    return {
        "total": int(len(calibraciones)),
        "vigentes": int(
            (calibraciones["estado"] == "Vigente").sum()
        ),
        "proximas": int(
            (
                calibraciones["estado"]
                == "Próxima a vencer"
            ).sum()
        ),
        "vencidas": int(
            (calibraciones["estado"] == "Vencida").sum()
        ),
        "sin_vencimiento": int(
            (
                calibraciones["estado"]
                == "Sin vencimiento"
            ).sum()
        ),
        "dias_restantes": min(dias_validos) if dias_validos else None,
    }