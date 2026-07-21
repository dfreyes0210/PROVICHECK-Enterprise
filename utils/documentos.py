from __future__ import annotations

import mimetypes
import re
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from database import get_connection

DOCUMENTOS_ROOT = Path("data") / "documentos"

def _seguro(valor):
    texto = re.sub(r"[^\w\-. ]", "_", str(valor or "").strip())
    return re.sub(r"\s+", "_", texto) or "sin_nombre"

def _fecha(valor):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor).strip() or None

def calcular_estado(fecha_vencimiento, dias_alerta=30):
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
    if dias <= dias_alerta:
        return "Próximo a vencer"
    return "Vigente"

def registrar_documento(codigo_equipo, tipo_documento, archivo_subido, titulo="", fecha_emision=None, fecha_vencimiento=None, responsable="", proveedor="", version="", observaciones=""):
    if archivo_subido is None:
        raise ValueError("Debe seleccionar un archivo.")
    carpeta = DOCUMENTOS_ROOT / _seguro(codigo_equipo)
    carpeta.mkdir(parents=True, exist_ok=True)
    original = Path(archivo_subido.name).name
    ext = Path(original).suffix.lower()
    guardado = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}_{_seguro(Path(original).stem)}{ext}"
    destino = carpeta / guardado
    destino.write_bytes(archivo_subido.getbuffer())
    mime = getattr(archivo_subido, "type", None) or mimetypes.guess_type(original)[0] or "application/octet-stream"
    ahora = datetime.now()
    estado = calcular_estado(fecha_vencimiento)
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO documentos_equipo (codigo_equipo,tipo_documento,titulo,nombre_archivo,ruta_archivo,mime_type,tamano_bytes,fecha_carga,hora_carga,fecha_emision,fecha_vencimiento,responsable,proveedor,version,observaciones,estado,activo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """,(str(codigo_equipo),str(tipo_documento),str(titulo or '').strip(),original,str(destino),mime,destino.stat().st_size,ahora.date().isoformat(),ahora.strftime('%H:%M:%S'),_fecha(fecha_emision),_fecha(fecha_vencimiento),str(responsable or '').strip(),str(proveedor or '').strip(),str(version or '').strip(),str(observaciones or '').strip(),estado))
        conn.commit(); return cur.lastrowid
    except Exception:
        conn.rollback(); destino.unlink(missing_ok=True); raise
    finally:
        conn.close()

def leer_documento(ruta_archivo):
    ruta=Path(str(ruta_archivo))
    if not ruta.exists():
        raise FileNotFoundError("El archivo físico no se encuentra disponible.")
    return ruta.read_bytes()

def eliminar_documento(documento_id):
    conn=get_connection(); cur=conn.cursor()
    fila=cur.execute("SELECT ruta_archivo FROM documentos_equipo WHERE id=?",(int(documento_id),)).fetchone()
    if fila is None:
        conn.close(); raise ValueError("El documento no existe.")
    cur.execute("UPDATE documentos_equipo SET activo=0 WHERE id=?",(int(documento_id),))
    conn.commit(); conn.close()
    Path(fila['ruta_archivo']).unlink(missing_ok=True)

def actualizar_estados_documentos(codigo_equipo):
    conn=get_connection(); cur=conn.cursor()
    filas=cur.execute("SELECT id,fecha_vencimiento FROM documentos_equipo WHERE activo=1 AND codigo_equipo=?",(str(codigo_equipo),)).fetchall()
    for fila in filas:
        cur.execute("UPDATE documentos_equipo SET estado=? WHERE id=?",(calcular_estado(fila['fecha_vencimiento']),fila['id']))
    conn.commit(); conn.close()