from __future__ import annotations

import mimetypes
import re
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from database import get_connection
from utils.data import cargar_hoja
from utils.persistencia_bitacora import registrar_evento_bitacora


DOCUMENTOS_ROOT = Path("data") / "documentos"


def _texto_seguro(valor, por_defecto=""):
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def _normalizar_codigo(valor):
    texto = _texto_seguro(valor)

    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base

    return texto


def _obtener_identidad_equipo(codigo_equipo):
    """
    Recupera nombre y laboratorio desde el Excel maestro.
    Si el equipo no se encuentra, devuelve textos vacíos sin bloquear
    el registro principal del documento.
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


def _seguro(valor):
    """Convierte textos en nombres seguros para carpetas y archivos."""
    texto = re.sub(r"[^\w\-. ]", "_", str(valor or "").strip())
    return re.sub(r"\s+", "_", texto) or "sin_nombre"


def _fecha(valor):
    """Normaliza fechas a formato ISO YYYY-MM-DD."""
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    return texto or None


def calcular_estado(fecha_vencimiento, dias_alerta=30):
    """Calcula el estado documental según su fecha de vencimiento."""
    fecha_txt = _fecha(fecha_vencimiento)
    if not fecha_txt:
        return "Sin vencimiento"
    try:
        vencimiento = date.fromisoformat(fecha_txt)
    except ValueError:
        return "Fecha inválida"
    dias = (vencimiento - date.today()).days
    if dias < 0:
        return "Vencido"
    if dias <= int(dias_alerta):
        return "Próximo a vencer"
    return "Vigente"


def registrar_documento(
    codigo_equipo,
    tipo_documento,
    archivo_subido,
    titulo="",
    fecha_emision=None,
    fecha_vencimiento=None,
    responsable="",
    proveedor="",
    version="",
    observaciones="",
):
    """Guarda el archivo físico y registra su información en SQLite."""
    if archivo_subido is None:
        raise ValueError("Debe seleccionar un archivo.")

    codigo = str(codigo_equipo or "").strip()
    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    tipo = str(tipo_documento or "").strip()
    if not tipo:
        raise ValueError("Debe indicar el tipo de documento.")

    carpeta = DOCUMENTOS_ROOT / _seguro(codigo)
    carpeta.mkdir(parents=True, exist_ok=True)

    original = Path(archivo_subido.name).name
    extension = Path(original).suffix.lower()
    nombre_guardado = (
        f"{datetime.now():%Y%m%d_%H%M%S}_"
        f"{uuid4().hex[:8]}_"
        f"{_seguro(Path(original).stem)}"
        f"{extension}"
    )

    destino = carpeta / nombre_guardado
    destino.write_bytes(archivo_subido.getbuffer())

    mime = (
        getattr(archivo_subido, "type", None)
        or mimetypes.guess_type(original)[0]
        or "application/octet-stream"
    )

    ahora = datetime.now()
    estado = calcular_estado(fecha_vencimiento)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO documentos_equipo (
                codigo_equipo,
                tipo_documento,
                titulo,
                nombre_archivo,
                ruta_archivo,
                mime_type,
                tamano_bytes,
                fecha_carga,
                hora_carga,
                fecha_emision,
                fecha_vencimiento,
                responsable,
                proveedor,
                version,
                observaciones,
                estado,
                activo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                codigo,
                tipo,
                str(titulo or "").strip(),
                original,
                str(destino),
                mime,
                destino.stat().st_size,
                ahora.date().isoformat(),
                ahora.strftime("%H:%M:%S"),
                _fecha(fecha_emision),
                _fecha(fecha_vencimiento),
                str(responsable or "").strip(),
                str(proveedor or "").strip(),
                str(version or "").strip(),
                str(observaciones or "").strip(),
                estado,
            ),
        )

        documento_id = cur.lastrowid

        conn.commit()

        nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(codigo)

        descripcion_bitacora = (
            f"Tipo: {tipo}. "
            f"Archivo: {original}. "
            f"Título: {_texto_seguro(titulo, 'Sin título')}. "
            f"Versión: {_texto_seguro(version, 'No registrada')}. "
            f"Proveedor o emisor: "
            f"{_texto_seguro(proveedor, 'No informado')}. "
            f"Fecha de emisión: {_fecha(fecha_emision) or 'No registrada'}. "
            f"Fecha de vencimiento: "
            f"{_fecha(fecha_vencimiento) or 'No aplica'}. "
            f"Estado documental: {estado}."
        )

        if estado == "Vencido":
            estado_bitacora = "Error"
        elif estado == "Próximo a vencer":
            estado_bitacora = "Advertencia"
        else:
            estado_bitacora = "Información"

        ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
            fecha=ahora.date(),
            hora=ahora.time().replace(microsecond=0),
            codigo_equipo=codigo,
            nombre_equipo=nombre_equipo,
            laboratorio=laboratorio_equipo,
            categoria="Documento",
            evento="Documento registrado",
            descripcion=descripcion_bitacora,
            usuario=str(responsable or "").strip(),
            estado=estado_bitacora,
            origen="Automático",
            id_referencia=f"DOC-{documento_id}",
        )

        if not ok_bitacora:
            raise RuntimeError(
                "El documento se guardó, pero no fue posible registrar "
                "el evento en la bitácora de Supabase. "
                f"Detalle: {mensaje_bitacora}"
            )

        return documento_id

    except Exception:
        conn.rollback()
        destino.unlink(missing_ok=True)
        raise

    finally:
        conn.close()


def listar_documentos(codigo_equipo=None, incluir_inactivos=False):
    """Consulta los documentos registrados y devuelve un DataFrame."""
    conn = get_connection()
    condiciones = []
    parametros = []

    if codigo_equipo not in (None, ""):
        condiciones.append("codigo_equipo = ?")
        parametros.append(str(codigo_equipo).strip())

    if not incluir_inactivos:
        condiciones.append("activo = 1")

    where_sql = ""
    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    consulta = f"""
        SELECT
            id,
            codigo_equipo,
            tipo_documento,
            titulo,
            nombre_archivo,
            ruta_archivo,
            mime_type,
            tamano_bytes,
            fecha_carga,
            hora_carga,
            fecha_emision,
            fecha_vencimiento,
            responsable,
            proveedor,
            version,
            observaciones,
            estado,
            activo
        FROM documentos_equipo
        {where_sql}
        ORDER BY fecha_carga DESC, hora_carga DESC, id DESC
    """

    try:
        cursor = conn.execute(consulta, parametros)
        filas = cursor.fetchall()
        columnas = [descripcion[0] for descripcion in cursor.description]
        datos = [dict(fila) for fila in filas]
        return pd.DataFrame(datos, columns=columnas)
    finally:
        conn.close()


def obtener_documento(documento_id):
    """Obtiene un documento registrado por su identificador."""
    conn = get_connection()
    try:
        fila = conn.execute(
            "SELECT * FROM documentos_equipo WHERE id = ?",
            (int(documento_id),),
        ).fetchone()
        return dict(fila) if fila is not None else None
    finally:
        conn.close()


def leer_documento(ruta_archivo):
    """Lee el archivo físico y devuelve sus bytes."""
    ruta = Path(str(ruta_archivo))
    if not ruta.exists():
        raise FileNotFoundError(
            "El archivo físico no se encuentra disponible. "
            "Puede haberse perdido tras un reinicio del servidor."
        )
    return ruta.read_bytes()


def eliminar_documento(documento_id, usuario=""):
    """Realiza borrado lógico en SQLite y elimina el archivo físico disponible."""
    conn = get_connection()
    cur = conn.cursor()

    try:
        fila = cur.execute(
            """
            SELECT codigo_equipo, tipo_documento, nombre_archivo, ruta_archivo
            FROM documentos_equipo
            WHERE id = ?
            """,
            (int(documento_id),),
        ).fetchone()

        if fila is None:
            raise ValueError("El documento no existe.")

        ahora = datetime.now()

        cur.execute(
            "UPDATE documentos_equipo SET activo = 0 WHERE id = ?",
            (int(documento_id),),
        )

        conn.commit()

        codigo_equipo = str(fila["codigo_equipo"])
        nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(
            codigo_equipo
        )

        ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
            fecha=ahora.date(),
            hora=ahora.time().replace(microsecond=0),
            codigo_equipo=codigo_equipo,
            nombre_equipo=nombre_equipo,
            laboratorio=laboratorio_equipo,
            categoria="Documento",
            evento="Documento eliminado",
            descripcion=(
                f"Tipo: {fila['tipo_documento']}. "
                f"Archivo: {fila['nombre_archivo']}. "
                "Registro desactivado lógicamente y archivo físico "
                "eliminado cuando estuvo disponible."
            ),
            usuario=str(usuario or "").strip(),
            estado="Acción administrativa",
            origen="Manual",
            id_referencia=f"DOC-{int(documento_id)}",
        )

        if not ok_bitacora:
            raise RuntimeError(
                "El documento fue desactivado, pero no fue posible "
                "registrar el evento en la bitácora de Supabase. "
                f"Detalle: {mensaje_bitacora}"
            )

        Path(fila["ruta_archivo"]).unlink(missing_ok=True)
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def actualizar_estados_documentos(codigo_equipo=None):
    """Actualiza el estado de todos los documentos activos."""
    conn = get_connection()
    cur = conn.cursor()

    try:
        if codigo_equipo in (None, ""):
            filas = cur.execute(
                """
                SELECT id, fecha_vencimiento
                FROM documentos_equipo
                WHERE activo = 1
                """
            ).fetchall()
        else:
            filas = cur.execute(
                """
                SELECT id, fecha_vencimiento
                FROM documentos_equipo
                WHERE activo = 1 AND codigo_equipo = ?
                """,
                (str(codigo_equipo).strip(),),
            ).fetchall()

        for fila in filas:
            cur.execute(
                "UPDATE documentos_equipo SET estado = ? WHERE id = ?",
                (calcular_estado(fila["fecha_vencimiento"]), fila["id"]),
            )

        conn.commit()
        return len(filas)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def resumen_documentos(codigo_equipo=None):
    """Devuelve indicadores básicos de gestión documental."""
    actualizar_estados_documentos(codigo_equipo)
    documentos = listar_documentos(codigo_equipo)

    if documentos.empty:
        return {
            "total": 0,
            "vigentes": 0,
            "proximos": 0,
            "vencidos": 0,
            "sin_vencimiento": 0,
            "archivos_disponibles": 0,
        }

    disponibilidad = documentos["ruta_archivo"].apply(
        lambda ruta: Path(str(ruta)).exists()
    )

    return {
        "total": int(len(documentos)),
        "vigentes": int((documentos["estado"] == "Vigente").sum()),
        "proximos": int((documentos["estado"] == "Próximo a vencer").sum()),
        "vencidos": int((documentos["estado"] == "Vencido").sum()),
        "sin_vencimiento": int(
            (documentos["estado"] == "Sin vencimiento").sum()
        ),
        "archivos_disponibles": int(disponibilidad.sum()),
    }