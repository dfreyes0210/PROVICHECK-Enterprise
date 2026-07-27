import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "provicheck.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def crear_base_datos():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
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
            """
        )

        cur.execute(
            """
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
                FOREIGN KEY (id_sesion)
                    REFERENCES sesiones_verificacion(id_sesion)
            )
            """
        )

        cur.execute(
            """
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
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documentos_equipo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_equipo TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                titulo TEXT,
                nombre_archivo TEXT NOT NULL,
                ruta_archivo TEXT NOT NULL,
                mime_type TEXT,
                tamano_bytes INTEGER,
                fecha_carga TEXT NOT NULL,
                hora_carga TEXT NOT NULL,
                fecha_emision TEXT,
                fecha_vencimiento TEXT,
                responsable TEXT,
                proveedor TEXT,
                version TEXT,
                observaciones TEXT,
                estado TEXT DEFAULT 'Sin vencimiento',
                activo INTEGER DEFAULT 1
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calibraciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_equipo TEXT NOT NULL,
                tipo_calibracion TEXT NOT NULL,
                numero_certificado TEXT,
                laboratorio_calibracion TEXT,
                laboratorio_acreditado INTEGER DEFAULT 0,
                organismo_acreditador TEXT,
                alcance_acreditado TEXT,
                responsable TEXT,
                fecha_calibracion TEXT NOT NULL,
                fecha_proxima_calibracion TEXT,
                frecuencia_meses INTEGER,
                resultado TEXT NOT NULL,
                incertidumbre TEXT,
                factor_cobertura TEXT,
                patron_utilizado TEXT,
                codigo_patron TEXT,
                certificado_patron TEXT,
                vencimiento_patron TEXT,
                documento_id INTEGER,
                observaciones TEXT,
                estado TEXT DEFAULT 'Sin vencimiento',
                fecha_registro TEXT NOT NULL,
                hora_registro TEXT NOT NULL,
                usuario_registro TEXT,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (documento_id)
                    REFERENCES documentos_equipo(id)
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documentos_equipo_codigo
            ON documentos_equipo(codigo_equipo)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documentos_equipo_vencimiento
            ON documentos_equipo(fecha_vencimiento)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_calibraciones_equipo
            ON calibraciones(codigo_equipo)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_calibraciones_proxima
            ON calibraciones(fecha_proxima_calibracion)
            """
        )


        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mantenimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_equipo TEXT NOT NULL,
                tipo_mantenimiento TEXT NOT NULL,
                estado_mantenimiento TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                hora_inicio TEXT,
                fecha_fin TEXT,
                hora_fin TEXT,
                realizado_por_tipo TEXT,
                responsable TEXT,
                proveedor TEXT,
                numero_orden TEXT,
                descripcion TEXT NOT NULL,
                causa TEXT,
                accion_realizada TEXT,
                resultado TEXT,
                componente TEXT,
                marca_componente TEXT,
                modelo_componente TEXT,
                serie_componente TEXT,
                cantidad INTEGER DEFAULT 1,
                costo_repuesto REAL DEFAULT 0,
                costo_mano_obra REAL DEFAULT 0,
                costo_otros REAL DEFAULT 0,
                costo_total REAL DEFAULT 0,
                horas_fuera_servicio REAL DEFAULT 0,
                documento_id INTEGER,
                observaciones TEXT,
                fecha_registro TEXT NOT NULL,
                hora_registro TEXT NOT NULL,
                usuario_registro TEXT,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (documento_id)
                    REFERENCES documentos_equipo(id)
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mantenimientos_equipo
            ON mantenimientos(codigo_equipo)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mantenimientos_fecha
            ON mantenimientos(fecha_inicio)
            """
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
