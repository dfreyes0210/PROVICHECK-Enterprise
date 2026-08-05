from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from utils.supabase_client import obtener_cliente_supabase


ESTADOS_BITACORA = {
    "Información",
    "Advertencia",
    "Error",
    "Acción administrativa",
}


def _serializar(valor: Any) -> Any:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, time):
        return valor.strftime("%H:%M:%S")
    if isinstance(valor, (str, int, float, bool)):
        return valor
    if hasattr(valor, "item"):
        try:
            return _serializar(valor.item())
        except Exception:
            pass
    texto = str(valor).strip()
    return None if texto.lower() in {"nan", "nat", "none"} else texto


def registrar_evento_bitacora(
    *,
    fecha: date | str,
    hora: time | str,
    codigo_equipo: str,
    nombre_equipo: str = "",
    laboratorio: str = "",
    categoria: str,
    evento: str,
    descripcion: str = "",
    usuario: str = "",
    estado: str = "Información",
    origen: str = "Automático",
    id_referencia: str | None = None,
) -> tuple[bool, str]:
    codigo_equipo = str(codigo_equipo or "").strip()
    categoria = str(categoria or "").strip()
    evento = str(evento or "").strip()
    estado = str(estado or "Información").strip()
    origen = str(origen or "Automático").strip()

    if not codigo_equipo:
        return False, "Falta el código del equipo."
    if not categoria:
        return False, "Falta la categoría del evento."
    if not evento:
        return False, "Falta el nombre del evento."
    if estado not in ESTADOS_BITACORA:
        estado = "Información"

    registro = {
        "fecha": _serializar(fecha),
        "hora": _serializar(hora),
        "codigo_equipo": codigo_equipo,
        "nombre_equipo": str(nombre_equipo or "").strip(),
        "laboratorio": str(laboratorio or "").strip(),
        "categoria": categoria,
        "evento": evento,
        "descripcion": str(descripcion or "").strip(),
        "usuario": str(usuario or "").strip(),
        "estado": estado,
        "origen": origen,
        "id_referencia": (
            str(id_referencia).strip()
            if id_referencia not in (None, "")
            else None
        ),
    }

    try:
        cliente = obtener_cliente_supabase()
        respuesta = cliente.table("bitacora").insert(registro).execute()
        if not (respuesta.data or []):
            return False, "Supabase no confirmó el registro."
        return True, "Evento registrado correctamente en la bitácora."
    except Exception as exc:
        return False, f"No fue posible registrar el evento: {exc}"


def registrar_eventos_verificacion(
    sesion: dict[str, Any],
    detalles: list[dict[str, Any]],
) -> tuple[bool, str]:
    if not sesion:
        return False, "No se recibió la información de la sesión."

    fecha = sesion.get("fecha")
    hora = sesion.get("hora")
    codigo = str(sesion.get("codigo_equipo", "")).strip()
    nombre = str(sesion.get("nombre_equipo", "")).strip()
    laboratorio = str(sesion.get("laboratorio", "")).strip()
    responsable = str(sesion.get("responsable", "")).strip()
    estado_sesion = str(sesion.get("estado", "")).strip()
    id_sesion = str(sesion.get("id_sesion", "")).strip()

    total = int(sesion.get("total_puntos", 0) or 0)
    cumplen = int(sesion.get("puntos_cumplen", 0) or 0)
    no_cumplen = int(sesion.get("puntos_no_cumplen", 0) or 0)
    no_evaluados = int(sesion.get("puntos_no_evaluados", 0) or 0)

    eventos = [
        {
            "evento": "Verificación guardada",
            "descripcion": (
                f"Sesión {id_sesion}: {total} punto(s), "
                f"{cumplen} cumple(n), {no_cumplen} no cumple(n) y "
                f"{no_evaluados} no evaluado(s)."
            ),
            "estado": "Información",
        }
    ]

    if estado_sesion == "Conforme":
        eventos.append({
            "evento": "Verificación conforme",
            "descripcion": f"La sesión {id_sesion} finalizó conforme.",
            "estado": "Información",
        })
    elif estado_sesion == "No conforme":
        eventos.append({
            "evento": "Verificación no conforme",
            "descripcion": (
                f"La sesión {id_sesion} presentó "
                f"{no_cumplen} punto(s) fuera de tolerancia."
            ),
            "estado": "Error",
        })
    elif estado_sesion == "Incompleta":
        eventos.append({
            "evento": "Verificación incompleta",
            "descripcion": (
                f"La sesión {id_sesion} presentó "
                f"{no_evaluados} punto(s) no evaluado(s)."
            ),
            "estado": "Advertencia",
        })

    novedades = []
    for detalle in detalles or []:
        observacion = str(detalle.get("observacion", "") or "").strip()
        punto = str(detalle.get("punto", "") or "").strip()
        estado_punto = str(detalle.get("estado_punto", "") or "").strip()
        if observacion and observacion != "Sin novedades":
            novedades.append(f"{punto}: {estado_punto} - {observacion}")

    if novedades:
        eventos.append({
            "evento": "Observación registrada",
            "descripcion": " | ".join(novedades),
            "estado": "Advertencia",
        })

    errores = []
    for item in eventos:
        ok, mensaje = registrar_evento_bitacora(
            fecha=fecha,
            hora=hora,
            codigo_equipo=codigo,
            nombre_equipo=nombre,
            laboratorio=laboratorio,
            categoria="Verificación",
            evento=item["evento"],
            descripcion=item["descripcion"],
            usuario=responsable,
            estado=item["estado"],
            origen="Automático",
            id_referencia=id_sesion,
        )
        if not ok:
            errores.append(mensaje)

    if errores:
        return False, " | ".join(errores)

    return True, (
        f"Bitácora actualizada con {len(eventos)} evento(s) "
        f"para la sesión {id_sesion}."
    )