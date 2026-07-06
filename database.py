import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "provicheck.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def crear_base_datos():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sesiones_verificacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_sesion TEXT UNIQUE,
        codigo_equipo TEXT,
        nombre_equipo TEXT,
        laboratorio TEXT,
        fecha TEXT,
        hora TEXT,
        responsable TEXT,
        estado TEXT,
        total_puntos INTEGER,
        puntos_cumplen INTEGER,
        puntos_no_cumplen INTEGER,
        puntos_no_evaluados INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS detalle_verificacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_sesion TEXT,
        codigo_equipo TEXT,
        punto TEXT,
        nombre_chequeo TEXT,
        valor_nominal REAL,
        resultado REAL,
        error REAL,
        limite_inferior REAL,
        limite_superior REAL,
        estado_punto TEXT,
        observacion TEXT,
        FOREIGN KEY (id_sesion) REFERENCES sesiones_verificacion(id_sesion)
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
        usuario TEXT,
        origen TEXT
    )
    """)

    conn.commit()
    conn.close()