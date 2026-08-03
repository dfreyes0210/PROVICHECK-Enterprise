from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from utils.supabase_client import obtener_cliente_supabase


def _serializar(valor: Any) -> Any:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, time):
        return valor.strftime("%H:%M:%S")
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (str, int, float, bool)):
        return valor
    if hasattr(valor, "item"):
        try:
            return _serializar(valor.item())
        except Exception:
            pass
    texto = str(valor).strip()
    return None if texto.lower() in {"nan", "nat", "none"} else texto


def guardar_sesion_supabase(
    sesion: dict[str, Any],
    detalles: list[dict[str, Any]],
) -> tuple[bool, str]:
    if not sesion:
        return False, "No se recibió información de la sesión."
    if not detalles:
        return False, "La sesión no contiene puntos de verificación."

    id_sesion = str(sesion.get("id_sesion", "")).strip()
    if not id_sesion:
        return False, "La sesión no tiene un identificador válido."

    sesion_json = {k: _serializar(v) for k, v in sesion.items()}
    sesion_json.setdefault("usuario_login", "")
    sesion_json.setdefault("total_puntos", 0)
    sesion_json.setdefault("puntos_cumplen", 0)
    sesion_json.setdefault("puntos_no_cumplen", 0)
    sesion_json.setdefault("puntos_no_evaluados", 0)

    campos = {
        "codigo_equipo", "punto", "nombre_chequeo", "codigo_patron",
        "estado_patron", "fecha_vencimiento_patron", "valor_nominal",
        "resultado", "error", "limite_inferior", "limite_superior",
        "estado_punto", "observacion",
    }

    detalles_json = []
    for detalle in detalles:
        limpio = {campo: _serializar(detalle.get(campo)) for campo in campos}
        limpio["codigo_equipo"] = limpio.get("codigo_equipo") or ""
        limpio["punto"] = limpio.get("punto") or "Punto sin nombre"
        limpio["estado_punto"] = limpio.get("estado_punto") or "No evaluado"
        limpio["observacion"] = limpio.get("observacion") or ""
        detalles_json.append(limpio)

    try:
        cliente = obtener_cliente_supabase()
        respuesta = cliente.rpc(
            "guardar_verificacion",
            {"p_sesion": sesion_json, "p_detalles": detalles_json},
        ).execute()

        datos = respuesta.data or {}
        cantidad = (
            datos.get("detalles_guardados")
            if isinstance(datos, dict)
            else len(detalles_json)
        )
        return True, (
            "Sesión guardada permanentemente en Supabase. "
            f"ID: {id_sesion}. Puntos guardados: {cantidad}."
        )

    except Exception as exc:
        mensaje = str(exc).strip()
        if "already exists" in mensaje.lower() or "ya existe" in mensaje.lower():
            return False, (
                f"La sesión {id_sesion} ya existe en Supabase. "
                "No se guardaron duplicados."
            )
        return False, (
            "No fue posible guardar la verificación en Supabase. "
            f"Detalle: {mensaje}"
        )


def probar_lectura_supabase() -> tuple[bool, str, list[dict[str, Any]]]:
    try:
        cliente = obtener_cliente_supabase()
        respuesta = (
            cliente.table("sesiones_verificacion")
            .select("id_sesion,codigo_equipo,fecha,hora,estado")
            .order("fecha_registro", desc=True)
            .limit(5)
            .execute()
        )
        return True, "Conexión de lectura con Supabase correcta.", respuesta.data or []
    except Exception as exc:
        return False, f"No fue posible consultar Supabase: {exc}", []