from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from database import get_connection


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
    codigo = str(codigo_equipo or "").strip()
    tipo = str(tipo_mantenimiento or "").strip()
    estado = str(estado_mantenimiento or "").strip()
    descripcion_txt = str(descripcion or "").strip()
    fecha_i = _fecha_iso(fecha_inicio)
    fecha_f = _fecha_iso(fecha_fin)

    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    if not tipo:
        raise ValueError("Debe indicar el tipo de mantenimiento.")

    if not estado:
        raise ValueError("Debe indicar el estado del mantenimiento.")

    if not fecha_i:
        raise ValueError("Debe indicar la fecha de inicio.")

    if not descripcion_txt:
        raise ValueError("Debe describir el mantenimiento.")

    horas_fuera = calcular_horas_fuera_servicio(
        fecha_i,
        hora_inicio,
        fecha_f,
        hora_fin,
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

    ahora = datetime.now()

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO mantenimientos (
                codigo_equipo,
                tipo_mantenimiento,
                estado_mantenimiento,
                fecha_inicio,
                hora_inicio,
                fecha_fin,
                hora_fin,
                realizado_por_tipo,
                responsable,
                proveedor,
                numero_orden,
                descripcion,
                causa,
                accion_realizada,
                resultado,
                componente,
                marca_componente,
                modelo_componente,
                serie_componente,
                cantidad,
                costo_repuesto,
                costo_mano_obra,
                costo_otros,
                costo_total,
                horas_fuera_servicio,
                documento_id,
                observaciones,
                fecha_registro,
                hora_registro,
                usuario_registro,
                activo
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1
            )
            """,
            (
                codigo,
                tipo,
                estado,
                fecha_i,
                _hora_texto(hora_inicio),
                fecha_f,
                _hora_texto(hora_fin),
                str(realizado_por_tipo or "").strip(),
                str(responsable or "").strip(),
                str(proveedor or "").strip(),
                str(numero_orden or "").strip(),
                descripcion_txt,
                str(causa or "").strip(),
                str(accion_realizada or "").strip(),
                str(resultado or "").strip(),
                str(componente or "").strip(),
                str(marca_componente or "").strip(),
                str(modelo_componente or "").strip(),
                str(serie_componente or "").strip(),
                int(cantidad or 1),
                costo_repuesto_num,
                costo_mano_obra_num,
                costo_otros_num,
                costo_total,
                horas_fuera,
                int(documento_id) if documento_id else None,
                str(observaciones or "").strip(),
                ahora.date().isoformat(),
                ahora.strftime("%H:%M:%S"),
                str(usuario_registro or "").strip(),
            ),
        )

        mantenimiento_id = int(cur.lastrowid)

        cur.execute(
            """
            INSERT INTO bitacora (
                fecha,
                hora,
                codigo_equipo,
                evento,
                detalle,
                usuario,
                origen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ahora.date().isoformat(),
                ahora.strftime("%H:%M:%S"),
                codigo,
                f"Mantenimiento {tipo}",
                (
                    f"{descripcion_txt} · "
                    f"Estado: {estado} · "
                    f"Resultado: {resultado or 'No informado'}"
                ),
                str(usuario_registro or responsable or "").strip(),
                "Mantenimientos",
            ),
        )

        conn.commit()
        return mantenimiento_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def listar_mantenimientos(
    codigo_equipo: Optional[str] = None,
    incluir_inactivos: bool = False,
) -> pd.DataFrame:
    condiciones = []
    parametros: List[Any] = []

    if codigo_equipo not in (None, ""):
        condiciones.append("m.codigo_equipo = ?")
        parametros.append(str(codigo_equipo).strip())

    if not incluir_inactivos:
        condiciones.append("m.activo = 1")

    where_sql = ""
    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    consulta = f"""
        SELECT
            m.*,
            d.nombre_archivo AS documento_nombre,
            d.ruta_archivo AS documento_ruta,
            d.mime_type AS documento_mime
        FROM mantenimientos m
        LEFT JOIN documentos_equipo d
            ON m.documento_id = d.id
        {where_sql}
        ORDER BY
            m.fecha_inicio DESC,
            m.hora_inicio DESC,
            m.id DESC
    """

    conn = get_connection()

    try:
        cursor = conn.execute(consulta, parametros)
        filas = cursor.fetchall()
        columnas = [item[0] for item in cursor.description]

        return pd.DataFrame(
            [dict(fila) for fila in filas],
            columns=columnas,
        )

    finally:
        conn.close()


def eliminar_mantenimiento(
    mantenimiento_id: int,
    usuario: str = "",
) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    try:
        fila = cur.execute(
            """
            SELECT
                codigo_equipo,
                tipo_mantenimiento,
                descripcion
            FROM mantenimientos
            WHERE id = ?
            """,
            (int(mantenimiento_id),),
        ).fetchone()

        if fila is None:
            raise ValueError("El mantenimiento no existe.")

        ahora = datetime.now()

        cur.execute(
            """
            UPDATE mantenimientos
            SET activo = 0
            WHERE id = ?
            """,
            (int(mantenimiento_id),),
        )

        cur.execute(
            """
            INSERT INTO bitacora (
                fecha,
                hora,
                codigo_equipo,
                evento,
                detalle,
                usuario,
                origen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ahora.date().isoformat(),
                ahora.strftime("%H:%M:%S"),
                fila["codigo_equipo"],
                "Mantenimiento eliminado",
                (
                    f"{fila['tipo_mantenimiento']} · "
                    f"{fila['descripcion']}"
                ),
                str(usuario or "").strip(),
                "Mantenimientos",
            ),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


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
                mantenimientos["costo_total"]
                .fillna(0)
                .sum()
            ),
            2,
        ),
        "horas_fuera_servicio": round(
            float(
                mantenimientos["horas_fuera_servicio"]
                .fillna(0)
                .sum()
            ),
            2,
        ),
        "ultimo_mantenimiento": (
            mantenimientos.iloc[0].get("fecha_inicio")
        ),
    }