import sqlite3
from pathlib import Path

# Ruta de la base de datos
DB_PATH = Path("data") / "provicheck.db"


def get_connection():
    """
    Retorna una conexión a la base de datos SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn