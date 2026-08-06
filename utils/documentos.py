from __future__ import annotations

import mimetypes
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from utils.data import cargar_hoja
from utils.persistencia_bitacora import registrar_evento_bitacora
from utils.supabase_client import obtener_cliente_supabase


BUCKET_DOCUMENTOS = "documentos-equipos"
LIMITE_ARCHIVO_BYTES = 20 * 1024 * 1024
ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def _ahora_colombia() -> datetime:
    return datetime.now(ZONA_COLOMBIA)


def _seguro(valor: Any) -> str:
    """Convierte textos en nombres seguros para rutas de Storage."""
    texto = re.sub(r"[^\w\-. ]", "_", str(valor or "").strip())
    return re.sub(r"\s+", "_", texto) or "sin_nombre"


def _texto_seguro(valor: Any, por_defecto: str = "") -> str:
    if valor is None:
        return por_defecto

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return por_defecto

    return texto


def _normalizar_codigo(valor: Any) -> str:
    texto = _texto_seguro(valor)

    if texto.endswith(".0"):
        base = texto[:-2]
        if base.replace("-", "").isdigit():
            return base

    return texto


def _fecha(valor: Any) -> str | None:
    """Normaliza fechas al formato ISO YYYY-MM-DD."""
    if valor in (None, ""):
        return None

    if isinstance(valor, datetime):
        return valor.date().isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    texto = str(valor).strip()
    return texto or None


def _obtener_identidad_equipo(codigo_equipo: str) -> tuple[str, str]:
    """Recupera nombre y laboratorio desde el Excel maestro."""
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


def _bytes_archivo(archivo_subido) -> bytes:
    if hasattr(archivo_subido, "getvalue"):
        contenido = archivo_subido.getvalue()
    elif hasattr(archivo_subido, "getbuffer"):
        contenido = bytes(archivo_subido.getbuffer())
    else:
        contenido = bytes(archivo_subido)

    if not contenido:
        raise ValueError("El archivo seleccionado está vacío.")

    if len(contenido) > LIMITE_ARCHIVO_BYTES:
        raise ValueError(
            "El archivo supera el límite permitido de 20 MB."
        )

    return contenido


def calcular_estado(
    fecha_vencimiento: Any,
    dias_alerta: int = 30,
) -> str:
    """Calcula el estado documental según su vencimiento."""
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
    """
    Carga el archivo al bucket privado de Supabase Storage y registra
    sus metadatos en public.documentos_equipo.
    """
    if archivo_subido is None:
        raise ValueError("Debe seleccionar un archivo.")

    codigo = _normalizar_codigo(codigo_equipo)
    tipo = _texto_seguro(tipo_documento)

    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    if not tipo:
        raise ValueError("Debe indicar el tipo de documento.")

    emision = _fecha(fecha_emision)
    vencimiento = _fecha(fecha_vencimiento)

    if emision and vencimiento and vencimiento < emision:
        raise ValueError(
            "La fecha de vencimiento no puede ser anterior "
            "a la fecha de emisión."
        )

    original = Path(archivo_subido.name).name
    extension = Path(original).suffix.lower()
    contenido = _bytes_archivo(archivo_subido)

    mime = (
        getattr(archivo_subido, "type", None)
        or mimetypes.guess_type(original)[0]
        or "application/octet-stream"
    )

    ahora = _ahora_colombia()
    nombre_guardado = (
        f"{ahora:%Y%m%d_%H%M%S}_"
        f"{uuid4().hex[:8]}_"
        f"{_seguro(Path(original).stem)}"
        f"{extension}"
    )
    ruta_storage = f"{_seguro(codigo)}/{nombre_guardado}"
    estado = calcular_estado(vencimiento)

    cliente = obtener_cliente_supabase()
    bucket = cliente.storage.from_(BUCKET_DOCUMENTOS)

    try:
        bucket.upload(
            path=ruta_storage,
            file=contenido,
            file_options={
                "content-type": mime,
                "upsert": "false",
            },
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible cargar el archivo en Supabase Storage. "
            f"Detalle: {exc}"
        ) from exc

    registro = {
        "codigo_equipo": codigo,
        "tipo_documento": tipo,
        "titulo": _texto_seguro(titulo),
        "nombre_archivo": original,
        "ruta_archivo": ruta_storage,
        "bucket": BUCKET_DOCUMENTOS,
        "mime_type": mime,
        "tamano_bytes": len(contenido),
        "fecha_carga": ahora.date().isoformat(),
        "hora_carga": ahora.strftime("%H:%M:%S"),
        "fecha_emision": emision,
        "fecha_vencimiento": vencimiento,
        "responsable": _texto_seguro(responsable),
        "proveedor": _texto_seguro(proveedor),
        "version": _texto_seguro(version),
        "observaciones": _texto_seguro(observaciones),
        "estado": estado,
        "usuario_registro": _texto_seguro(responsable),
        "activo": True,
    }

    try:
        respuesta = (
            cliente.table("documentos_equipo")
            .insert(registro)
            .execute()
        )
    except Exception as exc:
        try:
            bucket.remove([ruta_storage])
        except Exception:
            pass

        raise RuntimeError(
            "El archivo se cargó temporalmente, pero no fue posible "
            "registrar sus metadatos en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []

    if not datos:
        try:
            bucket.remove([ruta_storage])
        except Exception:
            pass

        raise RuntimeError(
            "Supabase no confirmó el registro del documento."
        )

    documento_id = int(datos[0]["id"])
    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(
        codigo
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
        descripcion=(
            f"Tipo: {tipo}. "
            f"Archivo: {original}. "
            f"Título: {_texto_seguro(titulo, 'Sin título')}. "
            f"Versión: {_texto_seguro(version, 'No registrada')}. "
            f"Proveedor o emisor: "
            f"{_texto_seguro(proveedor, 'No informado')}. "
            f"Fecha de emisión: {emision or 'No registrada'}. "
            f"Fecha de vencimiento: {vencimiento or 'No aplica'}. "
            f"Estado documental: {estado}."
        ),
        usuario=_texto_seguro(responsable),
        estado=estado_bitacora,
        origen="Automático",
        id_referencia=f"DOC-{documento_id}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "El documento quedó almacenado en Supabase, pero no fue "
            "posible registrar su evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return documento_id


def listar_documentos(
    codigo_equipo=None,
    incluir_inactivos=False,
) -> pd.DataFrame:
    """Consulta los documentos registrados en Supabase."""
    actualizar_estados_documentos(codigo_equipo)

    try:
        cliente = obtener_cliente_supabase()
        consulta = cliente.table("documentos_equipo").select("*")

        if codigo_equipo not in (None, ""):
            consulta = consulta.eq(
                "codigo_equipo",
                _normalizar_codigo(codigo_equipo),
            )

        if not incluir_inactivos:
            consulta = consulta.eq("activo", True)

        respuesta = (
            consulta.order("fecha_carga", desc=True)
            .order("hora_carga", desc=True)
            .order("id", desc=True)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar los documentos en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []

    if not datos:
        return pd.DataFrame()

    return pd.DataFrame(datos)


def obtener_documento(documento_id):
    """Obtiene un documento por su identificador."""
    try:
        respuesta = (
            obtener_cliente_supabase()
            .table("documentos_equipo")
            .select("*")
            .eq("id", int(documento_id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar el documento. "
            f"Detalle: {exc}"
        ) from exc

    datos = respuesta.data or []
    return datos[0] if datos else None


def leer_documento(ruta_archivo, bucket=BUCKET_DOCUMENTOS):
    """
    Descarga y devuelve los bytes de un archivo almacenado
    en un bucket privado de Supabase Storage.
    """
    ruta = _texto_seguro(ruta_archivo)

    if not ruta:
        raise FileNotFoundError(
            "El documento no tiene una ruta de almacenamiento válida."
        )

    try:
        contenido = (
            obtener_cliente_supabase()
            .storage.from_(bucket)
            .download(ruta)
        )
    except Exception as exc:
        raise FileNotFoundError(
            "El archivo no se encuentra disponible en Supabase Storage. "
            f"Detalle: {exc}"
        ) from exc

    if not contenido:
        raise FileNotFoundError(
            "Supabase Storage devolvió un archivo vacío."
        )

    return bytes(contenido)


def eliminar_documento(documento_id, usuario=""):
    """
    Realiza borrado lógico de los metadatos y elimina el archivo
    del bucket privado cuando está disponible.
    """
    documento = obtener_documento(documento_id)

    if documento is None:
        raise ValueError("El documento no existe.")

    if not bool(documento.get("activo", True)):
        return True

    cliente = obtener_cliente_supabase()
    ruta = _texto_seguro(documento.get("ruta_archivo"))
    bucket_nombre = _texto_seguro(
        documento.get("bucket"),
        BUCKET_DOCUMENTOS,
    )

    try:
        (
            cliente.table("documentos_equipo")
            .update({"activo": False})
            .eq("id", int(documento_id))
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible desactivar el documento en Supabase. "
            f"Detalle: {exc}"
        ) from exc

    if ruta:
        try:
            cliente.storage.from_(bucket_nombre).remove([ruta])
        except Exception as exc:
            try:
                (
                    cliente.table("documentos_equipo")
                    .update({"activo": True})
                    .eq("id", int(documento_id))
                    .execute()
                )
            except Exception:
                pass

            raise RuntimeError(
                "No fue posible eliminar el archivo de Supabase Storage. "
                f"Detalle: {exc}"
            ) from exc

    ahora = _ahora_colombia()
    codigo = _normalizar_codigo(documento.get("codigo_equipo"))
    nombre_equipo, laboratorio_equipo = _obtener_identidad_equipo(
        codigo
    )

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio_equipo,
        categoria="Documento",
        evento="Documento eliminado",
        descripcion=(
            f"Tipo: {documento.get('tipo_documento')}. "
            f"Archivo: {documento.get('nombre_archivo')}. "
            "Registro desactivado lógicamente y archivo eliminado "
            "de Supabase Storage."
        ),
        usuario=_texto_seguro(usuario),
        estado="Acción administrativa",
        origen="Manual",
        id_referencia=f"DOC-{int(documento_id)}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "El documento fue eliminado, pero no fue posible registrar "
            "el evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return True


def actualizar_estados_documentos(codigo_equipo=None):
    """Actualiza el estado de todos los documentos activos."""
    try:
        cliente = obtener_cliente_supabase()
        consulta = (
            cliente.table("documentos_equipo")
            .select("id,fecha_vencimiento,estado")
            .eq("activo", True)
        )

        if codigo_equipo not in (None, ""):
            consulta = consulta.eq(
                "codigo_equipo",
                _normalizar_codigo(codigo_equipo),
            )

        respuesta = consulta.execute()
    except Exception as exc:
        raise RuntimeError(
            "No fue posible consultar los estados documentales. "
            f"Detalle: {exc}"
        ) from exc

    filas = respuesta.data or []
    actualizados = 0

    for fila in filas:
        nuevo_estado = calcular_estado(
            fila.get("fecha_vencimiento")
        )

        if fila.get("estado") == nuevo_estado:
            continue

        try:
            (
                cliente.table("documentos_equipo")
                .update({"estado": nuevo_estado})
                .eq("id", int(fila["id"]))
                .execute()
            )
            actualizados += 1
        except Exception as exc:
            raise RuntimeError(
                "No fue posible actualizar el estado de un documento. "
                f"Detalle: {exc}"
            ) from exc

    return actualizados


def resumen_documentos(codigo_equipo=None):
    """Devuelve indicadores básicos de gestión documental."""
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

    return {
        "total": int(len(documentos)),
        "vigentes": int(
            (documentos["estado"] == "Vigente").sum()
        ),
        "proximos": int(
            (
                documentos["estado"]
                == "Próximo a vencer"
            ).sum()
        ),
        "vencidos": int(
            (documentos["estado"] == "Vencido").sum()
        ),
        "sin_vencimiento": int(
            (
                documentos["estado"]
                == "Sin vencimiento"
            ).sum()
        ),
        "archivos_disponibles": int(len(documentos)),
    }