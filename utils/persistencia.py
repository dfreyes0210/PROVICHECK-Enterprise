from datetime import datetime
from database import get_connection


def generar_id_sesion(codigo_equipo):
    ahora = datetime.now()
    return f"SES-{codigo_equipo}-{ahora.strftime('%Y%m%d-%H%M%S')}"


def guardar_sesion_sqlite(sesion, detalles):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO sesiones_verificacion (
                id_sesion,
                codigo_equipo,
                nombre_equipo,
                laboratorio,
                fecha,
                hora,
                responsable,
                estado,
                total_puntos,
                puntos_cumplen,
                puntos_no_cumplen,
                puntos_no_evaluados
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sesion["id_sesion"],
                sesion["codigo_equipo"],
                sesion["nombre_equipo"],
                sesion["laboratorio"],
                sesion["fecha"],
                sesion["hora"],
                sesion["responsable"],
                sesion["estado"],
                sesion["total_puntos"],
                sesion["puntos_cumplen"],
                sesion["puntos_no_cumplen"],
                sesion["puntos_no_evaluados"],
            ),
        )

        for detalle in detalles:
            cur.execute(
                """
                INSERT INTO detalle_verificacion (
                    id_sesion,
                    codigo_equipo,
                    punto,
                    nombre_chequeo,
                    valor_nominal,
                    resultado,
                    error,
                    limite_inferior,
                    limite_superior,
                    estado_punto,
                    observacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sesion["id_sesion"],
                    detalle["codigo_equipo"],
                    detalle["punto"],
                    detalle["nombre_chequeo"],
                    detalle["valor_nominal"],
                    detalle["resultado"],
                    detalle["error"],
                    detalle["limite_inferior"],
                    detalle["limite_superior"],
                    detalle["estado_punto"],
                    detalle["observacion"],
                ),
            )

            if detalle["estado_punto"] != "Cumple" or detalle["observacion"] != "Sin novedades":
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
                        sesion["fecha"],
                        sesion["hora"],
                        sesion["codigo_equipo"],
                        "Evento en verificación",
                        f"{detalle['punto']} - {detalle['estado_punto']} - {detalle['observacion']}",
                        sesion["responsable"],
                        "Verificación",
                    ),
                )

        conn.commit()
        return True, "Sesión guardada correctamente en SQLite."

    except Exception as e:
        conn.rollback()
        return False, f"Error guardando sesión: {e}"

    finally:
        conn.close()