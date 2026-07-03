import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "provicheck.db"


def get_connection():
    """
    Retorna una conexión SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def crear_base_datos():
    """
    Crea todas las tablas necesarias para PROVICHECK.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sesiones_verificacion (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        id_sesion TEXT,

        codigo_equipo TEXT,

        nombre_equipo TEXT,

        laboratorio TEXT,

        fecha TEXT,

        hora TEXT,

        responsable TEXT,

        estado TEXT

    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS detalle_verificacion (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        id_sesion TEXT,

        punto TEXT,

        nombre_chequeo TEXT,

        valor_nominal REAL,

        resultado REAL,

        error REAL,

        limite_inferior REAL,

        limite_superior REAL,

        estado_punto TEXT,

        observacion TEXT

    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bitacora (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        fecha TEXT,

        hora TEXT,

        codigo_equipo TEXT,

        evento TEXT,

        detalle TEXT,

        usuario TEXT

    )
    """)

    conn.commit()
    conn.close()