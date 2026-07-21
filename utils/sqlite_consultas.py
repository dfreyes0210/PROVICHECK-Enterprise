import pandas as pd
from database import get_connection


def consultar_sesiones_verificacion(limite=20):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM sesiones_verificacion
        ORDER BY fecha DESC, hora DESC
        LIMIT ?
        """,
        conn,
        params=(limite,),
    )
    conn.close()
    return df


def consultar_detalle_sesion(id_sesion):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM detalle_verificacion
        WHERE id_sesion = ?
        ORDER BY id
        """,
        conn,
        params=(id_sesion,),
    )
    conn.close()
    return df


def consultar_bitacora_equipo(codigo_equipo=None, limite=50):
    conn = get_connection()

    if codigo_equipo:
        df = pd.read_sql_query(
            """
            SELECT *
            FROM bitacora
            WHERE codigo_equipo = ?
            ORDER BY fecha DESC, hora DESC
            LIMIT ?
            """,
            conn,
            params=(codigo_equipo, limite),
        )
    else:
        df = pd.read_sql_query(
            """
            SELECT *
            FROM bitacora
            ORDER BY fecha DESC, hora DESC
            LIMIT ?
            """,
            conn,
            params=(limite,),
        )

    conn.close()
    return df


def consultar_ultima_verificacion(codigo_equipo):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM sesiones_verificacion
        WHERE codigo_equipo = ?
        ORDER BY fecha DESC, hora DESC
        LIMIT 1
        """,
        conn,
        params=(str(codigo_equipo),),
    )
    conn.close()
    return df


def consultar_historial_equipo(codigo_equipo, limite=20):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM sesiones_verificacion
        WHERE codigo_equipo = ?
        ORDER BY fecha DESC, hora DESC
        LIMIT ?
        """,
        conn,
        params=(str(codigo_equipo), limite),
    )
    conn.close()
    return df


def consultar_eventos_equipo(codigo_equipo, limite=20):
    return consultar_bitacora_equipo(str(codigo_equipo), limite)

def consultar_documentos_equipo(codigo_equipo, incluir_inactivos=False):
    conn = get_connection()
    filtro = "" if incluir_inactivos else "AND activo = 1"
    df = pd.read_sql_query(
        f"""
        SELECT *
        FROM documentos_equipo
        WHERE codigo_equipo = ?
        {filtro}
        ORDER BY fecha_carga DESC, hora_carga DESC, id DESC
        """, conn, params=(str(codigo_equipo),)
    )
    conn.close()
    return df


def consultar_documento_por_id(documento_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM documentos_equipo WHERE id = ? LIMIT 1",
        conn, params=(int(documento_id),)
    )
    conn.close()
    return df