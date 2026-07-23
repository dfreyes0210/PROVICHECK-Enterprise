from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from database import get_connection


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


def _fecha_iso(valor: Any) -> str | None:
    if valor in (None, ""):
        return None

    if isinstance(valor, datetime):
        return valor.date().isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    texto = str(valor).strip()
    return texto or None


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
    codigo = str(codigo_equipo or "").strip()
    tipo = str(tipo_calibracion or "").strip()
    resultado_txt = str(resultado or "").strip()
    fecha_cal = _fecha_iso(fecha_calibracion)
    fecha_proxima = _fecha_iso(fecha_proxima_calibracion)

    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    if not tipo:
        raise ValueError("Debe indicar el tipo de calibración.")

    if not fecha_cal:
        raise ValueError("Debe indicar la fecha de calibración.")

    if not resultado_txt:
        raise ValueError("Debe indicar el resultado de la calibración.")

    if fecha_proxima and fecha_proxima < fecha_cal:
        raise ValueError(
            "La próxima calibración no puede ser anterior "
            "a la fecha de calibración."
        )

    ahora = datetime.now()
    estado = calcular_estado_calibracion(fecha_proxima)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO calibraciones (
                codigo_equipo,
                tipo_calibracion,
                numero_certificado,
                laboratorio_calibracion,
                laboratorio_acreditado,
                organismo_acreditador,
                alcance_acreditado,
                responsable,
                fecha_calibracion,
                fecha_proxima_calibracion,
                frecuencia_meses,
                resultado,
                incertidumbre,
                factor_cobertura,
                patron_utilizado,
                codigo_patron,
                certificado_patron,
                vencimiento_patron,
                documento_id,
                observaciones,
                estado,
                fecha_registro,
                hora_registro,
                usuario_registro,
                activo
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, 1
            )
            """,
            (
                codigo,
                tipo,
                str(numero_certificado or "").strip(),
                str(laboratorio_calibracion or "").strip(),
                1 if laboratorio_acreditado else 0,
                str(organismo_acreditador or "").strip(),
                str(alcance_acreditado or "").strip(),
                str(responsable or "").strip(),
                fecha_cal,
                fecha_proxima,
                int(frecuencia_meses) if frecuencia_meses else None,
                resultado_txt,
                str(incertidumbre or "").strip(),
                str(factor_cobertura or "").strip(),
                str(patron_utilizado or "").strip(),
                str(codigo_patron or "").strip(),
                str(certificado_patron or "").strip(),
                _fecha_iso(vencimiento_patron),
                int(documento_id) if documento_id else None,
                str(observaciones or "").strip(),
                estado,
                ahora.date().isoformat(),
                ahora.strftime("%H:%M:%S"),
                str(usuario_registro or "").strip(),
            ),
        )

        calibracion_id = cur.lastrowid

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
                "Calibración registrada",
                (
                    f"{tipo} - "
                    f"{numero_certificado or 'Sin certificado'} - "
                    f"{resultado_txt}"
                ),
                str(usuario_registro or responsable or "").strip(),
                "Calibraciones",
            ),
        )

        conn.commit()
        return int(calibracion_id)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def listar_calibraciones(
    codigo_equipo: str | None = None,
    incluir_inactivas: bool = False,
) -> pd.DataFrame:
    actualizar_estados_calibraciones(codigo_equipo)

    condiciones = []
    parametros: list[Any] = []

    if codigo_equipo not in (None, ""):
        condiciones.append("c.codigo_equipo = ?")
        parametros.append(str(codigo_equipo).strip())

    if not incluir_inactivas:
        condiciones.append("c.activo = 1")

    where_sql = ""
    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    consulta = f"""
        SELECT
            c.*,
            d.nombre_archivo AS documento_nombre,
            d.ruta_archivo AS documento_ruta,
            d.mime_type AS documento_mime
        FROM calibraciones c
        LEFT JOIN documentos_equipo d
            ON c.documento_id = d.id
        {where_sql}
        ORDER BY
            c.fecha_calibracion DESC,
            c.id DESC
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


def actualizar_estados_calibraciones(
    codigo_equipo: str | None = None,
) -> int:
    conn = get_connection()
    cur = conn.cursor()

    try:
        if codigo_equipo in (None, ""):
            filas = cur.execute(
                """
                SELECT id, fecha_proxima_calibracion
                FROM calibraciones
                WHERE activo = 1
                """
            ).fetchall()
        else:
            filas = cur.execute(
                """
                SELECT id, fecha_proxima_calibracion
                FROM calibraciones
                WHERE activo = 1
                  AND codigo_equipo = ?
                """,
                (str(codigo_equipo).strip(),),
            ).fetchall()

        for fila in filas:
            cur.execute(
                """
                UPDATE calibraciones
                SET estado = ?
                WHERE id = ?
                """,
                (
                    calcular_estado_calibracion(
                        fila["fecha_proxima_calibracion"]
                    ),
                    fila["id"],
                ),
            )

        conn.commit()
        return len(filas)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def eliminar_calibracion(
    calibracion_id: int,
    usuario: str = "",
) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    try:
        fila = cur.execute(
            """
            SELECT
                codigo_equipo,
                tipo_calibracion,
                numero_certificado
            FROM calibraciones
            WHERE id = ?
            """,
            (int(calibracion_id),),
        ).fetchone()

        if fila is None:
            raise ValueError("La calibración no existe.")

        ahora = datetime.now()

        cur.execute(
            """
            UPDATE calibraciones
            SET activo = 0
            WHERE id = ?
            """,
            (int(calibracion_id),),
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
                "Calibración eliminada",
                (
                    f"{fila['tipo_calibracion']} - "
                    f"{fila['numero_certificado'] or 'Sin certificado'}"
                ),
                str(usuario or "").strip(),
                "Calibraciones",
            ),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


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