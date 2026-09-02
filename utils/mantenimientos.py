from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from uuid import uuid4
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from database import get_connection
from utils.data import cargar_hoja
from utils.persistencia_bitacora import registrar_evento_bitacora
from utils.supabase_client import obtener_cliente_supabase


ZONA_COLOMBIA = ZoneInfo("America/Bogota")

TIPOS_MANTENIMIENTO = [
    "Preventivo",
    "Correctivo",
    "Ajuste",
    "Cambio de componente",
    "Limpieza mayor",
    "Inspección técnica",
    "Calificación / Validación",
    "Instalación",
    "Traslado",
    "Baja temporal",
    "Baja definitiva",
    "Otro",
]

ESTADOS_MANTENIMIENTO = [
    "Programado",
    "En ejecución",
    "Finalizado",
    "Pendiente",
    "Cancelado",
]

RESULTADOS_MANTENIMIENTO = [
    "Equipo operativo",
    "Equipo operativo con observaciones",
    "Equipo fuera de servicio",
    "Requiere nueva intervención",
    "No aplica",
]

TIPOS_EJECUTOR = [
    "Personal interno",
    "Proveedor externo",
]


# EDITAR_MANTENIMIENTO_ADMIN_V1 — se reutilizan columnas existentes.
# Identidad, fechas originales, estado activo y usuario de creación no se editan.
CAMPOS_EDICION_MANTENIMIENTO = {
    "tipo_mantenimiento", "estado_mantenimiento", "realizado_por_tipo",
    "responsable", "proveedor", "numero_orden", "descripcion", "causa",
    "accion_realizada", "resultado", "componente", "marca_componente",
    "modelo_componente", "serie_componente", "cantidad", "costo_repuesto",
    "costo_mano_obra", "costo_otros", "documento_id", "observaciones",
}
CAMPOS_COSTOS_EDICION = {"costo_repuesto", "costo_mano_obra", "costo_otros"}


def puede_editar_mantenimientos() -> bool:
    from utils.permisos import obtener_rol_usuario

    # No aceptar Líder ni un rol recibido desde un formulario.
    return obtener_rol_usuario() == "Administrador"


def _usuario_editor() -> str:
    import streamlit as st

    if not puede_editar_mantenimientos():
        raise PermissionError("Solo el Administrador puede editar mantenimientos.")
    for clave in ("usuario_login", "usuario", "nombre_usuario", "usuario_nombre"):
        valor = st.session_state.get(clave)
        if isinstance(valor, str) and _texto_seguro(valor):
            return _texto_seguro(valor)
    raise PermissionError("No se identificó al usuario. Inicie sesión nuevamente.")


def obtener_mantenimiento_para_edicion(mantenimiento_id, codigo_equipo):
    """Lectura fresca, autorizada y limitada al equipo seleccionado."""
    _usuario_editor()
    respuesta = (
        obtener_cliente_supabase().table("mantenimientos").select("*")
        .eq("id", int(mantenimiento_id))
        .eq("codigo_equipo", _normalizar_codigo(codigo_equipo))
        .eq("activo", True).limit(1).execute()
    )
    if not respuesta.data:
        raise ValueError("El mantenimiento no existe, está inactivo o no es accesible.")
    return dict(respuesta.data[0])


def _valor_edicion(campo, valor):
    if campo in CAMPOS_COSTOS_EDICION or campo == "costo_total":
        try:
            numero = Decimal(str(0 if valor in (None, "") else valor))
            if not numero.is_finite() or numero < 0:
                raise ValueError("El costo debe ser finito y no negativo.")
            return float(numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Costo inválido en {campo}.") from exc
    if campo in {"cantidad", "documento_id"}:
        if valor in (None, ""):
            return None if campo == "documento_id" else 1
        try:
            numero = Decimal(str(valor))
            if not numero.is_finite() or numero != int(numero) or numero < 1:
                raise ValueError()
            return int(numero)
        except (InvalidOperation, ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"{campo} debe ser un entero positivo.") from exc
    return _texto_seguro(valor)


def actualizar_mantenimiento(mantenimiento_id, codigo_equipo, cambios, original, motivo):
    """Actualiza el mismo registro con permiso, trazabilidad y confirmación.

    'original' debe proceder de obtener_mantenimiento_para_edicion y guardarse
    en la sesión del servidor al abrir el editor; nunca se toma del navegador.
    No se requieren columnas nuevas. La bitácora registra primero la intención
    y luego su resultado: son operaciones separadas, no una transacción SQL.
    """
    usuario = _usuario_editor()  # Comprobación también en la capa de guardado.
    motivo = _texto_seguro(motivo)
    if len(motivo) < 10:
        raise ValueError("Indique un motivo de modificación de al menos 10 caracteres.")
    desconocidos = set(cambios) - CAMPOS_EDICION_MANTENIMIENTO
    if desconocidos:
        raise ValueError("Hay campos no permitidos para edición.")
    actual = obtener_mantenimiento_para_edicion(mantenimiento_id, codigo_equipo)
    if (str(original.get("id")) != str(actual["id"])
            or _normalizar_codigo(original.get("codigo_equipo")) != _normalizar_codigo(codigo_equipo)):
        raise ValueError("La copia original no corresponde al mantenimiento seleccionado.")
    for campo in CAMPOS_EDICION_MANTENIMIENTO | {"costo_total"}:
        if _valor_edicion(campo, actual.get(campo)) != _valor_edicion(campo, original.get(campo)):
            raise ValueError("El registro cambió desde que abrió el editor. Cancele y vuelva a abrirlo.")

    nuevos = dict(actual)
    nuevos.update({campo: _valor_edicion(campo, valor) for campo, valor in cambios.items()})
    for campo, opciones in (
        ("tipo_mantenimiento", TIPOS_MANTENIMIENTO),
        ("estado_mantenimiento", ESTADOS_MANTENIMIENTO),
        ("realizado_por_tipo", TIPOS_EJECUTOR),
        ("resultado", RESULTADOS_MANTENIMIENTO),
    ):
        if nuevos.get(campo) not in opciones:
            raise ValueError(f"Valor no válido en {campo}.")
    if not _texto_seguro(nuevos.get("descripcion")):
        raise ValueError("La descripción del mantenimiento es obligatoria.")
    if nuevos.get("realizado_por_tipo") == "Proveedor externo" and not _texto_seguro(nuevos.get("proveedor")):
        raise ValueError("Debe indicar el proveedor externo.")

    payload = {campo: nuevos[campo] for campo in cambios
               if _valor_edicion(campo, actual.get(campo)) != nuevos[campo]}
    if not payload:
        return {"actualizado": False, "aviso": "No hay cambios para guardar."}
    if set(payload) & CAMPOS_COSTOS_EDICION:
        payload["costo_total"] = float(sum(
            Decimal(str(_valor_edicion(campo, nuevos.get(campo))))
            for campo in CAMPOS_COSTOS_EDICION
        ))

    if "documento_id" in payload and payload["documento_id"] is not None:
        # No permitir asociar un soporte de otro equipo.
        conn = get_connection()
        try:
            documento = conn.execute(
                "SELECT codigo_equipo FROM documentos_equipo WHERE id = ?",
                (payload["documento_id"],),
            ).fetchone()
        finally:
            conn.close()
        if not documento or _normalizar_codigo(documento[0]) != _normalizar_codigo(codigo_equipo):
            raise ValueError("El documento no existe o pertenece a otro equipo.")

    operacion = uuid4().hex
    nombre, laboratorio = _obtener_identidad_equipo(codigo_equipo)
    detalle = json.dumps({
        "operacion": operacion, "motivo": motivo,
        "cambios": {k: {"anterior": actual.get(k), "nuevo": v} for k, v in payload.items()},
    }, ensure_ascii=False, default=str)

    def bitacora(evento, descripcion, estado):
        ahora = _ahora_colombia()
        return registrar_evento_bitacora(
            fecha=ahora.date(), hora=ahora.time().replace(microsecond=0),
            codigo_equipo=_normalizar_codigo(codigo_equipo), nombre_equipo=nombre,
            laboratorio=laboratorio, categoria="Mantenimiento", evento=evento,
            descripcion=descripcion, usuario=usuario, estado=estado,
            origen="Manual", id_referencia=f"MANT-{int(mantenimiento_id)}",
        )

    ok, _ = bitacora("Solicitud de edición de mantenimiento", detalle, "Acción administrativa")
    if not ok:
        raise RuntimeError("No se pudo registrar la trazabilidad. No se modificó el mantenimiento.")

    try:
        consulta = (obtener_cliente_supabase().table("mantenimientos").update(payload)
                    .eq("id", int(mantenimiento_id))
                    .eq("codigo_equipo", _normalizar_codigo(codigo_equipo)).eq("activo", True))
        # Compare-and-set: no sobrescribir modificaciones concurrentes de los
        # campos enviados. Se usan los valores originales, incluidos los NULL.
        campos_guardia = set(payload)
        if campos_guardia & CAMPOS_COSTOS_EDICION:
            campos_guardia |= CAMPOS_COSTOS_EDICION
        for campo in campos_guardia:
            valor = actual.get(campo)
            consulta = consulta.is_(campo, "null") if valor is None else consulta.eq(campo, valor)
        respuesta = consulta.execute()
        if not respuesta.data or len(respuesta.data) != 1:
            raise RuntimeError("Supabase no confirmó una fila actualizada. Revise permisos o cambios concurrentes.")
        confirmado = obtener_mantenimiento_para_edicion(mantenimiento_id, codigo_equipo)
        if any(_valor_edicion(k, confirmado.get(k)) != v for k, v in payload.items()):
            raise RuntimeError("La lectura posterior no coincide con los cambios enviados.")
    except Exception as exc:
        try:
            bitacora("Edición de mantenimiento no confirmada", f"Operación {operacion}. Revisar el registro antes de reintentar.", "Advertencia")
        except Exception:
            pass  # La solicitud con todos los cambios ya quedó registrada.
        raise RuntimeError("No se confirmó la edición. Recargue el historial antes de reintentar. " + str(exc)) from exc

    aviso = ""
    try:
        ok, _ = bitacora("Mantenimiento editado", detalle, "Acción administrativa")
        if not ok:
            aviso = "Los cambios están guardados; la solicitud quedó en bitácora, pero falló el evento de confirmación."
    except Exception:
        aviso = "Los cambios están guardados; la solicitud quedó en bitácora, pero falló el evento de confirmación."
    return {"actualizado": True, "aviso": aviso}


def _ahora_colombia() -> datetime:
    return datetime.now(ZONA_COLOMBIA)


def _fecha_iso(valor: Any) -> Optional[str]:
    if valor in (None, ""):
        return None

    if isinstance(valor, datetime):
        return valor.date().isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    texto = str(valor).strip()
    return texto or None


def _hora_texto(valor: Any) -> Optional[str]:
    if valor in (None, ""):
        return None

    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M:%S")

    texto = str(valor).strip()
    return texto or None


def _numero(valor: Any, defecto: float = 0.0) -> float:
    if valor in (None, ""):
        return float(defecto)

    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(defecto)


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
    """
    Recupera nombre y laboratorio desde el Excel maestro.
    Si no encuentra el equipo, devuelve textos vacíos sin bloquear
    el registro del mantenimiento.
    """
    try:
        equipos = cargar_hoja("Equipos")

        if equipos.empty or "codigo_equipo" not in equipos.columns:
            return "", ""

        codigo = _normalizar_codigo(codigo_equipo)

        coincidencias = equipos[
            equipos["codigo_equipo"]
            .apply(_normalizar_codigo)
            .eq(codigo)
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


def _consultar_documentos_sqlite() -> pd.DataFrame:
    """
    Transición controlada: los documentos todavía viven en SQLite.
    Devuelve metadatos para asociarlos al historial de mantenimientos.
    """
    conn = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT
                id,
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
                "id",
                "documento_nombre",
                "documento_ruta",
                "documento_mime",
            ]
        )
    finally:
        conn.close()


def calcular_horas_fuera_servicio(
    fecha_inicio: Any,
    hora_inicio: Any,
    fecha_fin: Any,
    hora_fin: Any,
) -> float:
    fecha_i = _fecha_iso(fecha_inicio)
    fecha_f = _fecha_iso(fecha_fin)
    hora_i = _hora_texto(hora_inicio)
    hora_f = _hora_texto(hora_fin)

    if not fecha_i or not fecha_f:
        return 0.0

    hora_i = hora_i or "00:00:00"
    hora_f = hora_f or "00:00:00"

    try:
        inicio = datetime.fromisoformat(f"{fecha_i} {hora_i}")
        fin = datetime.fromisoformat(f"{fecha_f} {hora_f}")
    except ValueError:
        return 0.0

    if fin < inicio:
        raise ValueError(
            "La fecha y hora de finalización no pueden ser "
            "anteriores al inicio."
        )

    return round((fin - inicio).total_seconds() / 3600, 2)


def registrar_mantenimiento(
    codigo_equipo: str,
    tipo_mantenimiento: str,
    estado_mantenimiento: str,
    fecha_inicio: Any,
    hora_inicio: Any,
    fecha_fin: Any,
    hora_fin: Any,
    realizado_por_tipo: str,
    responsable: str,
    proveedor: str,
    numero_orden: str,
    descripcion: str,
    causa: str,
    accion_realizada: str,
    resultado: str,
    componente: str,
    marca_componente: str,
    modelo_componente: str,
    serie_componente: str,
    cantidad: int,
    costo_repuesto: float,
    costo_mano_obra: float,
    costo_otros: float,
    documento_id: Optional[int],
    observaciones: str,
    usuario_registro: str = "",
) -> int:
    codigo = _normalizar_codigo(codigo_equipo)
    tipo = _texto_seguro(tipo_mantenimiento)
    estado = _texto_seguro(estado_mantenimiento)
    descripcion_txt = _texto_seguro(descripcion)
    resultado_txt = _texto_seguro(resultado)
    ejecutor_txt = _texto_seguro(realizado_por_tipo)
    fecha_i = _fecha_iso(fecha_inicio)
    fecha_f = _fecha_iso(fecha_fin)
    hora_i = _hora_texto(hora_inicio)
    hora_f = _hora_texto(hora_fin)

    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    if tipo not in TIPOS_MANTENIMIENTO:
        raise ValueError("El tipo de mantenimiento no es válido.")

    if estado not in ESTADOS_MANTENIMIENTO:
        raise ValueError("El estado del mantenimiento no es válido.")

    if not fecha_i:
        raise ValueError("Debe indicar la fecha de inicio.")

    if not descripcion_txt:
        raise ValueError("Debe describir el mantenimiento.")

    if ejecutor_txt not in TIPOS_EJECUTOR:
        raise ValueError("El tipo de ejecutor no es válido.")

    if resultado_txt not in RESULTADOS_MANTENIMIENTO:
        raise ValueError("El resultado del mantenimiento no es válido.")

    proveedor_txt = _texto_seguro(proveedor)

    if ejecutor_txt == "Proveedor externo" and not proveedor_txt:
        raise ValueError(
            "Debe registrar el proveedor o empresa que realizó "
            "el mantenimiento."
        )

    horas_fuera = calcular_horas_fuera_servicio(
        fecha_i,
        hora_i,
        fecha_f,
        hora_f,
    )

    costo_repuesto_num = _numero(costo_repuesto)
    costo_mano_obra_num = _numero(costo_mano_obra)
    costo_otros_num = _numero(costo_otros)
    costo_total = round(
        costo_repuesto_num
        + costo_mano_obra_num
        + costo_otros_num,
        2,
    )

    ahora = _ahora_colombia()

    registro = {
        "codigo_equipo": codigo,
        "tipo_mantenimiento": tipo,
        "estado_mantenimiento": estado,
        "fecha_inicio": fecha_i,
        "hora_inicio": hora_i,
        "fecha_fin": fecha_f,
        "hora_fin": hora_f,
        "realizado_por_tipo": ejecutor_txt,
        "responsable": _texto_seguro(responsable),
        "proveedor": proveedor_txt,
        "numero_orden": _texto_seguro(numero_orden),
        "descripcion": descripcion_txt,
        "causa": _texto_seguro(causa),
        "accion_realizada": _texto_seguro(accion_realizada),
        "resultado": resultado_txt,
        "componente": _texto_seguro(componente),
        "marca_componente": _texto_seguro(marca_componente),
        "modelo_componente": _texto_seguro(modelo_componente),
        "serie_componente": _texto_seguro(serie_componente),
        "cantidad": int(cantidad or 1),
        "costo_repuesto": costo_repuesto_num,
        "costo_mano_obra": costo_mano_obra_num,
        "costo_otros": costo_otros_num,
        "costo_total": costo_total,
        "horas_fuera_servicio": horas_fuera,
        "documento_id": int(documento_id) if documento_id else None,
        "observaciones": _texto_seguro(observaciones),
        "fecha_registro": ahora.date().isoformat(),
        "hora_registro": ahora.strftime("%H:%M:%S"),
        "usuario_registro": _texto_seguro(usuario_registro),
        "activo": True,
    }

    try:
        cliente = obtener_cliente_supabase()
        respuesta = (
            cliente.table("mantenimientos")
            .insert(registro)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible guardar el mantenimiento en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []

    if not datos:
        raise RuntimeError(
            "Supabase no confirmó el registro del mantenimiento."
        )

    mantenimiento_id = int(datos[0]["id"])

    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(
        codigo
    )

    if resultado_txt == "Equipo fuera de servicio":
        estado_bitacora = "Error"
    elif resultado_txt in {
        "Equipo operativo con observaciones",
        "Requiere nueva intervención",
    }:
        estado_bitacora = "Advertencia"
    else:
        estado_bitacora = "Información"

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio_equipo,
        categoria="Mantenimiento",
        evento=f"Mantenimiento {tipo}",
        descripcion=(
            f"Descripción: {descripcion_txt}. "
            f"Estado: {estado}. "
            f"Resultado: {resultado_txt}. "
            f"Ejecutor: {ejecutor_txt}. "
            f"Proveedor: {proveedor_txt or 'No informado'}. "
            f"Orden: {_texto_seguro(numero_orden, 'No registrada')}. "
            f"Componente: "
            f"{_texto_seguro(componente, 'No aplica')}. "
            f"Horas fuera de servicio: {horas_fuera:.2f}. "
            f"Costo total: {costo_total:.2f}."
        ),
        usuario=_texto_seguro(
            usuario_registro or responsable
        ),
        estado=estado_bitacora,
        origen="Automático",
        id_referencia=f"MANT-{mantenimiento_id}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "El mantenimiento quedó guardado en Supabase, pero no fue "
            "posible registrar su evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return mantenimiento_id


def listar_mantenimientos(
    codigo_equipo: Optional[str] = None,
    incluir_inactivos: bool = False,
) -> pd.DataFrame:
    try:
        cliente = obtener_cliente_supabase()
        consulta = cliente.table("mantenimientos").select("*")

        if codigo_equipo not in (None, ""):
            consulta = consulta.eq(
                "codigo_equipo",
                _normalizar_codigo(codigo_equipo),
            )

        if not incluir_inactivos:
            consulta = consulta.eq("activo", True)

        respuesta = (
            consulta.order("fecha_inicio", desc=True)
            .order("hora_inicio", desc=True)
            .order("id", desc=True)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar los mantenimientos en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []

    if not datos:
        return pd.DataFrame()

    mantenimientos = pd.DataFrame(datos)
    documentos = _consultar_documentos_sqlite()

    if (
        not documentos.empty
        and "documento_id" in mantenimientos.columns
    ):
        mantenimientos = mantenimientos.merge(
            documentos,
            how="left",
            left_on="documento_id",
            right_on="id",
            suffixes=("", "_documento"),
        )

        if "id_documento" in mantenimientos.columns:
            mantenimientos = mantenimientos.drop(
                columns=["id_documento"]
            )

    return mantenimientos


def eliminar_mantenimiento(
    mantenimiento_id: int,
    usuario: str = "",
) -> bool:
    cliente = obtener_cliente_supabase()

    try:
        respuesta = (
            cliente.table("mantenimientos")
            .select(
                "id,codigo_equipo,tipo_mantenimiento,"
                "descripcion,activo"
            )
            .eq("id", int(mantenimiento_id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar el mantenimiento. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []

    if not datos:
        raise ValueError("El mantenimiento no existe.")

    fila = datos[0]

    if not bool(fila.get("activo", True)):
        return True

    try:
        (
            cliente.table("mantenimientos")
            .update({"activo": False})
            .eq("id", int(mantenimiento_id))
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible desactivar el mantenimiento en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    ahora = _ahora_colombia()
    codigo = _normalizar_codigo(fila.get("codigo_equipo"))
    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(
        codigo
    )

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio_equipo,
        categoria="Mantenimiento",
        evento="Mantenimiento eliminado",
        descripcion=(
            f"Tipo: {fila.get('tipo_mantenimiento')}. "
            f"Descripción: {fila.get('descripcion')}. "
            "Registro desactivado lógicamente en PROVICHECK."
        ),
        usuario=_texto_seguro(usuario),
        estado="Acción administrativa",
        origen="Manual",
        id_referencia=f"MANT-{int(mantenimiento_id)}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "El mantenimiento fue desactivado en Supabase, pero no fue "
            "posible registrar el evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return True


def resumen_mantenimientos(
    codigo_equipo: Optional[str] = None,
) -> Dict[str, Any]:
    mantenimientos = listar_mantenimientos(codigo_equipo)

    if mantenimientos.empty:
        return {
            "total": 0,
            "preventivos": 0,
            "correctivos": 0,
            "costo_total": 0.0,
            "horas_fuera_servicio": 0.0,
            "ultimo_mantenimiento": None,
        }

    return {
        "total": int(len(mantenimientos)),
        "preventivos": int(
            (
                mantenimientos["tipo_mantenimiento"]
                == "Preventivo"
            ).sum()
        ),
        "correctivos": int(
            (
                mantenimientos["tipo_mantenimiento"]
                == "Correctivo"
            ).sum()
        ),
        "costo_total": round(
            float(
                pd.to_numeric(
                    mantenimientos["costo_total"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            ),
            2,
        ),
        "horas_fuera_servicio": round(
            float(
                pd.to_numeric(
                    mantenimientos["horas_fuera_servicio"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            ),
            2,
        ),
        "ultimo_mantenimiento": (
            mantenimientos.iloc[0].get("fecha_inicio")
        ),
    }
