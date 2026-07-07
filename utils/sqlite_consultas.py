import pandas as pd

from database import get_connection


def consultar_sesiones_verificacion(limite=20):
    conn = get_connection()

    query = """
        SELECT
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
        FROM sesiones_verificacion
        ORDER BY fecha DESC, hora DESC
        LIMIT ?
    """

    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()

    return df


def consultar_detalle_sesion(id_sesion):
    conn = get_connection()

    query = """
        SELECT
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
        FROM detalle_verificacion
        WHERE id_sesion = ?
        ORDER BY id
    """

    df = pd.read_sql_query(query, conn, params=(id_sesion,))
    conn.close()

    return df


def consultar_bitacora_equipo(codigo_equipo=None, limite=50):
    conn = get_connection()

    if codigo_equipo:
        query = """
            SELECT
                fecha,
                hora,
                codigo_equipo,
                evento,
                detalle,
                usuario,
                origen
            FROM bitacora
            WHERE codigo_equipo = ?
            ORDER BY fecha DESC, hora DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(codigo_equipo, limite))
    else:
        query = """
            SELECT
                fecha,
                hora,
                codigo_equipo,
                evento,
                detalle,
                usuario,
                origen
            FROM bitacora
            ORDER BY fecha DESC, hora DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limite,))

    conn.close()

    return df