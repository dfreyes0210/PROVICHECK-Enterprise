from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from utils.data import cargar_hoja
from utils.persistencia_bitacora import registrar_evento_bitacora
from utils.supabase_client import obtener_cliente_supabase


BUCKET_FOTOS = "fotos-equipos"
LIMITE_FOTO_BYTES = 6 * 1024 * 1024
MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def _ahora_colombia() -> datetime:
    return datetime.now(ZONA_COLOMBIA)


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


def _ruta_foto(codigo_equipo: Any) -> str:
    codigo = _normalizar_codigo(codigo_equipo)
    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")
    return f"{codigo}/foto_principal"


def _bytes_archivo(archivo_subido) -> bytes:
    if archivo_subido is None:
        raise ValueError("Debe seleccionar una fotografía.")

    if hasattr(archivo_subido, "getvalue"):
        contenido = archivo_subido.getvalue()
    elif hasattr(archivo_subido, "getbuffer"):
        contenido = bytes(archivo_subido.getbuffer())
    else:
        contenido = bytes(archivo_subido)

    if not contenido:
        raise ValueError("La fotografía seleccionada está vacía.")

    if len(contenido) > LIMITE_FOTO_BYTES:
        raise ValueError("La fotografía supera el límite permitido de 6 MB.")

    return contenido


def _mime_foto(archivo_subido) -> str:
    mime = _texto_seguro(getattr(archivo_subido, "type", None)).lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in MIME_PERMITIDOS:
        raise ValueError("Formato no permitido. Use JPG, JPEG, PNG o WEBP.")
    return mime


def _obtener_identidad_equipo(codigo_equipo: Any) -> tuple[str, str]:
    try:
        equipos = cargar_hoja("Equipos")
        if equipos.empty or "codigo_equipo" not in equipos.columns:
            return "", ""

        codigo = _normalizar_codigo(codigo_equipo)
        coincidencias = equipos[
            equipos["codigo_equipo"].apply(_normalizar_codigo).eq(codigo)
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


def guardar_foto_equipo(codigo_equipo: Any, archivo_subido, usuario: str = "") -> str:
    codigo = _normalizar_codigo(codigo_equipo)
    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    contenido = _bytes_archivo(archivo_subido)
    mime = _mime_foto(archivo_subido)
    ruta = _ruta_foto(codigo)

    cliente = obtener_cliente_supabase()
    bucket = cliente.storage.from_(BUCKET_FOTOS)

    try:
        bucket.upload(
            path=ruta,
            file=contenido,
            file_options={"content-type": mime, "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(
            "No fue posible guardar la fotografía en Supabase Storage. "
            f"Detalle: {exc}"
        ) from exc

    ahora = _ahora_colombia()
    nombre_equipo, laboratorio = _obtener_identidad_equipo(codigo)

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio,
        categoria="Equipo",
        evento="Fotografía actualizada",
        descripcion=(
            "Se cargó o reemplazó la fotografía principal del equipo "
            f"en Supabase Storage. Formato: {mime}. "
            f"Tamaño: {len(contenido)} bytes."
        ),
        usuario=_texto_seguro(usuario),
        estado="Información",
        origen="Manual",
        id_referencia=f"FOTO-{codigo}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "La fotografía quedó guardada en Supabase, pero no fue "
            "posible registrar el evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return ruta


def leer_foto_equipo(codigo_equipo: Any) -> bytes | None:
    codigo = _normalizar_codigo(codigo_equipo)
    if not codigo:
        return None

    ruta = _ruta_foto(codigo)

    try:
        contenido = (
            obtener_cliente_supabase()
            .storage.from_(BUCKET_FOTOS)
            .download(ruta)
        )
    except Exception:
        return None

    if not contenido:
        return None

    return bytes(contenido)


def foto_equipo_existe(codigo_equipo: Any) -> bool:
    return leer_foto_equipo(codigo_equipo) is not None


def eliminar_foto_equipo(codigo_equipo: Any, usuario: str = "") -> bool:
    codigo = _normalizar_codigo(codigo_equipo)
    if not codigo:
        raise ValueError("Debe indicar el código del equipo.")

    ruta = _ruta_foto(codigo)
    cliente = obtener_cliente_supabase()

    try:
        cliente.storage.from_(BUCKET_FOTOS).remove([ruta])
    except Exception as exc:
        raise RuntimeError(
            "No fue posible eliminar la fotografía de Supabase Storage. "
            f"Detalle: {exc}"
        ) from exc

    ahora = _ahora_colombia()
    nombre_equipo, laboratorio = _obtener_identidad_equipo(codigo)

    ok_bitacora, mensaje_bitacora = registrar_evento_bitacora(
        fecha=ahora.date(),
        hora=ahora.time().replace(microsecond=0),
        codigo_equipo=codigo,
        nombre_equipo=nombre_equipo,
        laboratorio=laboratorio,
        categoria="Equipo",
        evento="Fotografía eliminada",
        descripcion=(
            "Se eliminó la fotografía principal del equipo "
            "de Supabase Storage."
        ),
        usuario=_texto_seguro(usuario),
        estado="Acción administrativa",
        origen="Manual",
        id_referencia=f"FOTO-{codigo}",
    )

    if not ok_bitacora:
        raise RuntimeError(
            "La fotografía fue eliminada, pero no fue posible registrar "
            "el evento en la bitácora. "
            f"Detalle: {mensaje_bitacora}"
        )

    return True