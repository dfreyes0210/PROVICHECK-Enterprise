from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from database import get_connection
from utils.documentos import (
    actualizar_estados_documentos,
    eliminar_documento,
    leer_documento,
    listar_documentos,
    registrar_documento,
    resumen_documentos,
)

st.set_page_config(
    page_title="Documentos | PROVICHECK",
    page_icon="📂",
    layout="wide",
)

TIPOS_DOCUMENTO = [
    "Certificado de calibración",
    "Certificado de mantenimiento",
    "Manual del fabricante",
    "Procedimiento",
    "Instructivo",
    "Ficha técnica",
    "Hoja de seguridad",
    "Informe técnico",
    "Fotografía",
    "Registro de auditoría",
    "Otro",
]

def obtener_usuario_actual():
    for clave in ("usuario", "username", "nombre_usuario", "user"):
        valor = st.session_state.get(clave)
        if isinstance(valor, dict):
            for subclave in ("nombre", "usuario", "username", "email"):
                if valor.get(subclave):
                    return str(valor[subclave])
        if valor:
            return str(valor)
    return "Usuario PROVICHECK"

def cargar_equipos():
    conn = get_connection()
    try:
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(equipos)").fetchall()}
        codigo_col = next((n for n in ("codigo_equipo", "codigo", "id_equipo") if n in columnas), None)
        nombre_col = next((n for n in ("nombre_equipo", "nombre", "equipo") if n in columnas), None)
        laboratorio_col = next((n for n in ("laboratorio", "nombre_laboratorio", "area") if n in columnas), None)
        estado_col = next((n for n in ("estado", "activo") if n in columnas), None)

        if codigo_col is None:
            raise RuntimeError("No se encontró la columna de código en la tabla equipos.")

        nombre_sql = f'"{nombre_col}"' if nombre_col else "''"
        laboratorio_sql = f'"{laboratorio_col}"' if laboratorio_col else "''"

        where_sql = ""
        if estado_col == "activo":
            where_sql = 'WHERE "activo" = 1'
        elif estado_col == "estado":
            where_sql = """
                WHERE LOWER(COALESCE("estado", 'activo'))
                NOT IN ('inactivo', 'retirado', 'fuera de servicio')
            """

        consulta = f"""
            SELECT
                "{codigo_col}" AS codigo_equipo,
                {nombre_sql} AS nombre_equipo,
                {laboratorio_sql} AS laboratorio
            FROM equipos
            {where_sql}
            ORDER BY "{codigo_col}"
        """

        filas = conn.execute(consulta).fetchall()
        return pd.DataFrame(
            [dict(fila) for fila in filas],
            columns=["codigo_equipo", "nombre_equipo", "laboratorio"],
        )
    finally:
        conn.close()

def formato_tamano(bytes_archivo):
    try:
        valor = float(bytes_archivo or 0)
    except (TypeError, ValueError):
        return "0 KB"
    for unidad in ["B", "KB", "MB", "GB"]:
        if valor < 1024 or unidad == "GB":
            return f"{valor:.1f} {unidad}"
        valor /= 1024
    return "0 KB"

def etiqueta_estado(estado):
    mapa = {
        "Vigente": "🟢 Vigente",
        "Próximo a vencer": "🟡 Próximo a vencer",
        "Vencido": "🔴 Vencido",
        "Sin vencimiento": "🔵 Sin vencimiento",
        "Fecha inválida": "⚫ Fecha inválida",
    }
    return mapa.get(str(estado), f"⚪ {estado}")

def render_metricas(resumen):
    columnas = st.columns(5)
    columnas[0].metric("Documentos", resumen["total"])
    columnas[1].metric("Vigentes", resumen["vigentes"])
    columnas[2].metric("Próximos a vencer", resumen["proximos"])
    columnas[3].metric("Vencidos", resumen["vencidos"])
    columnas[4].metric("Archivos disponibles", resumen["archivos_disponibles"])

def render_registro(codigo_equipo):
    with st.expander("➕ Registrar documento", expanded=False):
        with st.form("form_registro_documento", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                tipo_documento = st.selectbox("Tipo de documento *", TIPOS_DOCUMENTO)
                titulo = st.text_input("Título", placeholder="Ejemplo: Certificado de calibración 2026")
                proveedor = st.text_input("Proveedor o emisor")
                version = st.text_input("Versión", placeholder="Ejemplo: 01")

            with col2:
                responsable = st.text_input("Responsable", value=obtener_usuario_actual())
                usa_fecha_emision = st.checkbox("Registrar fecha de emisión", value=True)
                fecha_emision = st.date_input("Fecha de emisión", value=date.today()) if usa_fecha_emision else None
                usa_vencimiento = st.checkbox("El documento tiene vencimiento", value=False)
                fecha_vencimiento = (
                    st.date_input(
                        "Fecha de vencimiento",
                        value=date.today(),
                        min_value=fecha_emision or date(2000, 1, 1),
                    )
                    if usa_vencimiento
                    else None
                )

            observaciones = st.text_area(
                "Observaciones",
                placeholder="Información adicional, alcance, restricciones o notas relevantes.",
            )

            archivo = st.file_uploader(
                "Seleccionar archivo *",
                type=["pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg", "webp", "txt", "zip"],
                help="Tamaño recomendado máximo: 20 MB.",
            )

            enviar = st.form_submit_button(
                "📤 Registrar documento",
                type="primary",
                use_container_width=True,
            )

        if enviar:
            if archivo is None:
                st.error("Debe seleccionar un archivo.")
                return

            try:
                registrar_documento(
                    codigo_equipo=codigo_equipo,
                    tipo_documento=tipo_documento,
                    archivo_subido=archivo,
                    titulo=titulo,
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    responsable=responsable,
                    proveedor=proveedor,
                    version=version,
                    observaciones=observaciones,
                )
                st.success("Documento registrado correctamente.")
                st.rerun()
            except Exception as error:
                st.error(f"No fue posible registrar el documento. Detalle: {error}")

def aplicar_filtros(documentos):
    if documentos.empty:
        return documentos

    col1, col2, col3 = st.columns(3)
    tipos = sorted(documentos["tipo_documento"].dropna().astype(str).unique().tolist())
    estados = sorted(documentos["estado"].dropna().astype(str).unique().tolist())

    with col1:
        filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos"] + tipos)
    with col2:
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos"] + estados)
    with col3:
        texto = st.text_input("Buscar", placeholder="Título, archivo, proveedor...")

    filtrados = documentos.copy()

    if filtro_tipo != "Todos":
        filtrados = filtrados[filtrados["tipo_documento"] == filtro_tipo]
    if filtro_estado != "Todos":
        filtrados = filtrados[filtrados["estado"] == filtro_estado]

    if texto.strip():
        patron = texto.strip().lower()
        columnas_busqueda = ["titulo", "nombre_archivo", "proveedor", "responsable", "observaciones"]
        mascara = pd.Series(False, index=filtrados.index)
        for columna in columnas_busqueda:
            if columna in filtrados.columns:
                mascara = mascara | (
                    filtrados[columna]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(patron, regex=False)
                )
        filtrados = filtrados[mascara]

    return filtrados

def render_documento(documento):
    documento_id = int(documento["id"])
    titulo = str(documento.get("titulo") or "").strip()
    nombre_archivo = str(documento.get("nombre_archivo") or "")
    encabezado = titulo or nombre_archivo

    with st.container(border=True):
        col_info, col_estado = st.columns([4, 1])

        with col_info:
            st.markdown(f"### 📄 {encabezado}")
            st.caption(nombre_archivo)

        with col_estado:
            st.markdown(f"**{etiqueta_estado(documento.get('estado'))}**")

        meta1, meta2, meta3, meta4 = st.columns(4)
        meta1.markdown(f"**Tipo**  \n{documento.get('tipo_documento') or '—'}")
        meta2.markdown(f"**Emisión**  \n{documento.get('fecha_emision') or '—'}")
        meta3.markdown(f"**Vencimiento**  \n{documento.get('fecha_vencimiento') or 'No aplica'}")
        meta4.markdown(f"**Tamaño**  \n{formato_tamano(documento.get('tamano_bytes'))}")

        proveedor = documento.get("proveedor") or "—"
        responsable = documento.get("responsable") or "—"
        version = documento.get("version") or "—"

        st.caption(f"Proveedor: {proveedor} · Responsable: {responsable} · Versión: {version}")

        observaciones = str(documento.get("observaciones") or "").strip()
        if observaciones:
            with st.expander("Ver observaciones"):
                st.write(observaciones)

        ruta = documento.get("ruta_archivo")
        archivo_existe = Path(str(ruta)).exists()

        col_descarga, col_elimina, col_aviso = st.columns([1.3, 1.1, 3])

        with col_descarga:
            if archivo_existe:
                try:
                    contenido = leer_documento(ruta)
                    st.download_button(
                        "⬇️ Descargar",
                        data=contenido,
                        file_name=nombre_archivo,
                        mime=documento.get("mime_type") or "application/octet-stream",
                        key=f"descargar_{documento_id}",
                        use_container_width=True,
                    )
                except Exception as error:
                    st.error(str(error))
            else:
                st.button(
                    "Archivo no disponible",
                    disabled=True,
                    key=f"no_disponible_{documento_id}",
                    use_container_width=True,
                )

        with col_elimina:
            confirmar = st.checkbox("Confirmar eliminación", key=f"confirmar_{documento_id}")
            if st.button(
                "🗑️ Eliminar",
                key=f"eliminar_{documento_id}",
                disabled=not confirmar,
                use_container_width=True,
            ):
                try:
                    eliminar_documento(documento_id, usuario=obtener_usuario_actual())
                    st.success("Documento eliminado.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No fue posible eliminar el documento. Detalle: {error}")

        with col_aviso:
            if not archivo_existe:
                st.warning(
                    "El registro existe en SQLite, pero el archivo físico no está disponible en este despliegue."
                )

def main():
    st.title("📂 Gestión documental")
    st.caption("Biblioteca técnica de equipos · PROVICHECK Enterprise")

    try:
        equipos = cargar_equipos()
    except Exception as error:
        st.error(f"No fue posible consultar los equipos. Detalle: {error}")
        st.stop()

    if equipos.empty:
        st.warning("No existen equipos disponibles para asociar documentos.")
        st.stop()

    equipos["etiqueta"] = equipos.apply(
        lambda fila: (
            f"{fila['codigo_equipo']} - {fila['nombre_equipo'] or 'Equipo sin nombre'}"
            + (f" · {fila['laboratorio']}" if str(fila["laboratorio"] or "").strip() else "")
        ),
        axis=1,
    )

    opciones = dict(zip(equipos["etiqueta"], equipos["codigo_equipo"]))
    seleccion = st.selectbox("Equipo", list(opciones.keys()), index=0)
    codigo_equipo = opciones[seleccion]

    try:
        actualizar_estados_documentos(codigo_equipo)
        resumen = resumen_documentos(codigo_equipo)
    except Exception as error:
        st.error(f"No fue posible consultar la gestión documental. Detalle: {error}")
        st.stop()

    render_metricas(resumen)
    st.divider()
    render_registro(codigo_equipo)
    st.subheader("📚 Biblioteca documental")

    try:
        documentos = listar_documentos(codigo_equipo)
    except Exception as error:
        st.error(f"No fue posible consultar los documentos. Detalle: {error}")
        st.stop()

    if documentos.empty:
        st.info("Este equipo todavía no tiene documentos registrados.")
        return

    filtrados = aplicar_filtros(documentos)
    st.caption(f"Mostrando {len(filtrados)} de {len(documentos)} documentos.")

    if filtrados.empty:
        st.warning("No existen documentos que coincidan con los filtros.")
        return

    for documento in filtrados.to_dict("records"):
        render_documento(documento)

if __name__ == "__main__":
    main()