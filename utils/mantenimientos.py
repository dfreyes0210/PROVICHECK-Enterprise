from __future__ import annotations

from datetime import date, datetime
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