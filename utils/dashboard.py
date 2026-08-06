from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from utils.data import cargar_hoja
from utils.supabase_client import obtener_cliente_supabase
from utils.supabase_consultas import (
    consultar_bitacora_equipo,
    consultar_detalle_sesion,
    consultar_sesiones_verificacion,
)

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def _ahora():
    return datetime.now(ZONA_COLOMBIA)


def _txt(v, d=""):
    if v is None:
        return d
    t = str(v).strip()
    return d if not t or t.lower() in {"nan", "nat", "none"} else t


def _codigo(v):
    t = _txt(v)
    if t.endswith(".0") and t[:-2].replace("-", "").isdigit():
        return t[:-2]
    return t


def _buscar_columna(df, opciones):
    mapa = {str(c).strip().lower(): c for c in df.columns}
    for opcion in opciones:
        if opcion.lower() in mapa:
            return mapa[opcion.lower()]
    return None


def _frecuencia_a_dias(valor):
    texto = _txt(valor).lower()
    if not texto or texto in {"nan", "none", "sin definir"}:
        return None
    equivalencias = {
        "diaria": 1, "diario": 1, "semanal": 7, "quincenal": 15,
        "mensual": 30, "bimestral": 60, "trimestral": 90,
        "cuatrimestral": 120, "semestral": 180, "anual": 365,
    }
    for nombre, dias in equivalencias.items():
        if nombre in texto:
            return dias
    numero = re.search(r"(\d+)", texto)
    if not numero:
        return None
    n = int(numero.group(1))
    if "semana" in texto:
        return n * 7
    if "mes" in texto:
        return n * 30
    if "año" in texto or "ano" in texto:
        return n * 365
    return n


def _equipos():
    df = cargar_hoja("Equipos")
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "codigo_equipo" in df.columns:
        df["codigo_equipo"] = df["codigo_equipo"].apply(_codigo)
    return df


def _tabla(nombre, activos=False):
    try:
        q = obtener_cliente_supabase().table(nombre).select("*")
        if activos:
            q = q.eq("activo", True)
        r = q.limit(100000).execute()
        return pd.DataFrame(r.data or [])
    except Exception:
        return pd.DataFrame()


def obtener_kpis():
    equipos = _equipos()
    sesiones = consultar_sesiones_verificacion(100000)
    activos = 0
    if not equipos.empty and "estado" in equipos.columns:
        activos = int(equipos["estado"].astype(str).str.lower().str.contains(
            "activo|operativo|disponible", na=False
        ).sum())
    estados = sesiones.get("estado", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    conformes = int((estados == "conforme").sum())
    no_conformes = int((estados == "no conforme").sum())
    incompletas = int((estados == "incompleta").sum())
    cerradas = conformes + no_conformes
    programacion = obtener_resumen_programacion()
    return {
        "equipos": int(len(equipos)),
        "activos": activos,
        "verificaciones": int(len(sesiones)),
        "conformes": conformes,
        "no_conformes": no_conformes,
        "incompletas": incompletas,
        "alertas": no_conformes + incompletas + programacion["vencidas"] + programacion["sin_verificar"],
        "porcentaje_conformidad": round(conformes / cerradas * 100, 1) if cerradas else 0.0,
    }


def obtener_ultimas_verificaciones(limite=10):
    return consultar_sesiones_verificacion(limite)


def obtener_bitacora_reciente(limite=10):
    df = consultar_bitacora_equipo(None, limite)
    if df.empty:
        return df
    df = df.copy()
    if "descripcion" in df.columns:
        df["detalle"] = df["descripcion"]
    if "categoria" in df.columns:
        df["origen"] = df["categoria"]
    return df


def obtener_equipos_por_laboratorio():
    equipos = _equipos()
    if equipos.empty or "laboratorio" not in equipos.columns:
        return pd.DataFrame(columns=["laboratorio", "cantidad"])
    return (equipos.assign(laboratorio=equipos["laboratorio"].fillna("Sin laboratorio"))
            .groupby("laboratorio").size().reset_index(name="cantidad")
            .sort_values("cantidad", ascending=False))


def obtener_estado_verificaciones():
    sesiones = consultar_sesiones_verificacion(100000)
    if sesiones.empty or "estado" not in sesiones.columns:
        return pd.DataFrame(columns=["estado", "cantidad"])
    return (sesiones.assign(estado=sesiones["estado"].fillna("Sin estado"))
            .groupby("estado").size().reset_index(name="cantidad"))


def _tipo_frecuencia_periodo(valor):
    texto = _txt(valor).lower()

    if not texto or texto in {"nan", "none", "sin definir"}:
        return "sin_frecuencia"

    reglas = [
        ("diaria", ["diaria", "diario", "cada día", "cada dia"]),
        ("semanal", ["semanal", "cada semana"]),
        ("quincenal", ["quincenal", "cada quincena"]),
        ("mensual", ["mensual", "cada mes"]),
        ("bimestral", ["bimestral", "cada 2 meses"]),
        ("trimestral", ["trimestral", "cada 3 meses"]),
        ("cuatrimestral", ["cuatrimestral", "cada 4 meses"]),
        ("semestral", ["semestral", "cada 6 meses"]),
        ("anual", ["anual", "cada año", "cada ano"]),
    ]

    for tipo, expresiones in reglas:
        if any(expresion in texto for expresion in expresiones):
            return tipo

    if re.search(r"\d+", texto):
        return "intervalo"

    return "sin_frecuencia"


def _periodo_actual(tipo, hoy=None):
    hoy = pd.Timestamp(hoy or _ahora().date()).normalize()
    anio = hoy.year
    mes = hoy.month

    if tipo == "diaria":
        inicio = fin = hoy
        etiqueta = hoy.strftime("%d/%m/%Y")

    elif tipo == "semanal":
        inicio = hoy - pd.Timedelta(days=hoy.weekday())
        fin = inicio + pd.Timedelta(days=6)
        semana = int(hoy.isocalendar().week)
        etiqueta = f"Semana {semana} de {anio}"

    elif tipo == "quincenal":
        if hoy.day <= 15:
            inicio = pd.Timestamp(anio, mes, 1)
            fin = pd.Timestamp(anio, mes, 15)
            etiqueta = f"1.ª quincena {hoy.strftime('%m/%Y')}"
        else:
            inicio = pd.Timestamp(anio, mes, 16)
            fin = pd.Timestamp(anio, mes, 1) + pd.offsets.MonthEnd(1)
            etiqueta = f"2.ª quincena {hoy.strftime('%m/%Y')}"

    elif tipo == "mensual":
        inicio = pd.Timestamp(anio, mes, 1)
        fin = inicio + pd.offsets.MonthEnd(1)
        etiqueta = hoy.strftime("%B %Y").capitalize()

    elif tipo in {"bimestral", "trimestral", "cuatrimestral", "semestral"}:
        meses_periodo = {
            "bimestral": 2,
            "trimestral": 3,
            "cuatrimestral": 4,
            "semestral": 6,
        }[tipo]
        bloque = (mes - 1) // meses_periodo
        mes_inicio = bloque * meses_periodo + 1
        inicio = pd.Timestamp(anio, mes_inicio, 1)
        fin = inicio + pd.DateOffset(months=meses_periodo) - pd.Timedelta(days=1)
        numero = bloque + 1
        nombres = {
            "bimestral": "Bimestre",
            "trimestral": "Trimestre",
            "cuatrimestral": "Cuatrimestre",
            "semestral": "Semestre",
        }
        etiqueta = f"{nombres[tipo]} {numero} de {anio}"

    elif tipo == "anual":
        inicio = pd.Timestamp(anio, 1, 1)
        fin = pd.Timestamp(anio, 12, 31)
        etiqueta = str(anio)

    else:
        return pd.NaT, pd.NaT, "Sin período"

    return inicio.normalize(), pd.Timestamp(fin).normalize(), etiqueta


def obtener_proximas_verificaciones():
    """
    Evalúa el cumplimiento por período calendario, no por suma fija de días.

    Ejemplos:
    - Mensual: una verificación en cualquier fecha del mes actual.
    - Trimestral: una verificación en cualquier fecha del trimestre actual.
    - Semestral: una verificación en cualquier fecha del semestre actual.
    """
    equipos = _equipos()
    sesiones = consultar_sesiones_verificacion(100000)

    if equipos.empty:
        return pd.DataFrame()

    c_codigo = _buscar_columna(equipos, ["codigo_equipo", "codigo"])
    c_nombre = _buscar_columna(equipos, ["nombre_equipo", "nombre", "equipo"])
    c_lab = _buscar_columna(equipos, ["laboratorio"])
    c_frec = _buscar_columna(
        equipos,
        ["frecuencia_verificacion", "frecuencia"],
    )

    if c_codigo is None:
        return pd.DataFrame()

    salida = pd.DataFrame({
        "codigo_equipo": equipos[c_codigo].apply(_codigo),
        "nombre_equipo": (
            equipos[c_nombre].fillna("Sin nombre").astype(str)
            if c_nombre is not None else "Sin nombre"
        ),
        "laboratorio": (
            equipos[c_lab].fillna("Sin laboratorio").astype(str)
            if c_lab is not None else "Sin laboratorio"
        ),
        "frecuencia": (
            equipos[c_frec].fillna("Sin definir").astype(str)
            if c_frec is not None else "Sin definir"
        ),
    })

    salida["tipo_periodo"] = salida["frecuencia"].apply(
        _tipo_frecuencia_periodo
    )

    hoy = pd.Timestamp(_ahora().date()).normalize()

    periodos = salida["tipo_periodo"].apply(
        lambda tipo: _periodo_actual(tipo, hoy)
    )
    salida["inicio_periodo"] = periodos.apply(lambda x: x[0])
    salida["fin_periodo"] = periodos.apply(lambda x: x[1])
    salida["periodo"] = periodos.apply(lambda x: x[2])

    salida["ultima_verificacion"] = pd.NaT
    salida["fecha_cumplimiento"] = pd.NaT
    salida["responsable_cumplimiento"] = ""

    if (
        not sesiones.empty
        and "codigo_equipo" in sesiones.columns
        and "fecha" in sesiones.columns
    ):
        historial = sesiones.copy()
        historial["codigo_equipo"] = historial["codigo_equipo"].apply(_codigo)
        historial["fecha_dt"] = pd.to_datetime(
            historial["fecha"],
            errors="coerce",
            dayfirst=True,
        ).dt.normalize()
        historial = historial.dropna(subset=["fecha_dt"])

        ultimas = (
            historial.groupby("codigo_equipo")["fecha_dt"]
            .max()
        )
        salida["ultima_verificacion"] = salida["codigo_equipo"].map(ultimas)

        def cumplimiento_equipo(fila):
            tipo = fila["tipo_periodo"]
            codigo = fila["codigo_equipo"]

            if tipo == "sin_frecuencia":
                return pd.NaT, ""

            registros = historial[
                historial["codigo_equipo"].eq(codigo)
            ].copy()

            if registros.empty:
                return pd.NaT, ""

            if tipo == "intervalo":
                ultima = registros.sort_values(
                    "fecha_dt",
                    ascending=False,
                ).iloc[0]
                return (
                    ultima["fecha_dt"],
                    str(ultima.get("responsable", "") or ""),
                )

            inicio = fila["inicio_periodo"]
            fin = fila["fin_periodo"]

            registros = registros[
                registros["fecha_dt"].between(inicio, fin)
            ]

            if registros.empty:
                return pd.NaT, ""

            ultimo = registros.sort_values(
                ["fecha_dt", "hora"] if "hora" in registros.columns else ["fecha_dt"],
                ascending=False,
            ).iloc[0]

            return (
                ultimo["fecha_dt"],
                str(ultimo.get("responsable", "") or ""),
            )

        cumplimientos = salida.apply(cumplimiento_equipo, axis=1)
        salida["fecha_cumplimiento"] = cumplimientos.apply(lambda x: x[0])
        salida["responsable_cumplimiento"] = cumplimientos.apply(lambda x: x[1])

    def estado_periodo(fila):
        tipo = fila["tipo_periodo"]

        if tipo == "sin_frecuencia":
            return "⚪ Sin frecuencia"

        if tipo == "intervalo":
            dias = _frecuencia_a_dias(fila["frecuencia"])
            ultima = fila["ultima_verificacion"]

            if dias is None:
                return "⚪ Sin frecuencia"
            if pd.isna(ultima):
                return "🔴 Sin verificar"

            proxima = ultima + pd.Timedelta(days=dias)
            return (
                "🟢 Cumplido"
                if proxima >= hoy
                else "🔴 Vencido por intervalo"
            )

        return (
            "🟢 Cumplido"
            if pd.notna(fila["fecha_cumplimiento"])
            else "🟡 Pendiente del período"
        )

    salida["estado_programacion"] = salida.apply(
        estado_periodo,
        axis=1,
    )

    salida["dias_restantes_periodo"] = salida.apply(
        lambda fila: (
            int((fila["fin_periodo"] - hoy).days)
            if pd.notna(fila["fin_periodo"])
            else None
        ),
        axis=1,
    )

    orden = {
        "🔴 Vencido por intervalo": 1,
        "🔴 Sin verificar": 2,
        "🟡 Pendiente del período": 3,
        "🟢 Cumplido": 4,
        "⚪ Sin frecuencia": 5,
    }
    salida["orden"] = salida["estado_programacion"].map(orden).fillna(9)

    return (
        salida.sort_values(
            ["orden", "laboratorio", "codigo_equipo"],
            na_position="last",
        )
        .drop(columns=["orden"])
        .reset_index(drop=True)
    )


def obtener_resumen_programacion():
    programacion = obtener_proximas_verificaciones()

    resumen = {
        "programados": 0,
        "cumplidos": 0,
        "pendientes": 0,
        "vencidos_intervalo": 0,
        "sin_verificar": 0,
        "sin_frecuencia": 0,
        "porcentaje_cumplimiento": 0.0,
        # Compatibilidad con la Dashboard anterior
        "vigentes": 0,
        "proximas": 0,
        "vencidas": 0,
    }

    if programacion.empty:
        return resumen

    estados = programacion["estado_programacion"].astype(str)

    resumen["cumplidos"] = int(
        estados.str.contains("Cumplido", na=False).sum()
    )
    resumen["pendientes"] = int(
        estados.str.contains("Pendiente del período", na=False).sum()
    )
    resumen["vencidos_intervalo"] = int(
        estados.str.contains("Vencido por intervalo", na=False).sum()
    )
    resumen["sin_verificar"] = int(
        estados.str.contains("Sin verificar", na=False).sum()
    )
    resumen["sin_frecuencia"] = int(
        estados.str.contains("Sin frecuencia", na=False).sum()
    )
    resumen["programados"] = (
        resumen["cumplidos"]
        + resumen["pendientes"]
        + resumen["vencidos_intervalo"]
        + resumen["sin_verificar"]
    )

    if resumen["programados"] > 0:
        resumen["porcentaje_cumplimiento"] = round(
            resumen["cumplidos"]
            / resumen["programados"]
            * 100,
            1,
        )

    resumen["vigentes"] = resumen["cumplidos"]
    resumen["proximas"] = resumen["pendientes"]
    resumen["vencidas"] = resumen["vencidos_intervalo"]

    return resumen


def obtener_agenda_critica(limite=20):
    programacion = obtener_proximas_verificaciones()

    if programacion.empty:
        return programacion

    estados_prioritarios = {
        "🔴 Vencido por intervalo",
        "🔴 Sin verificar",
        "🟡 Pendiente del período",
    }

    agenda = programacion[
        programacion["estado_programacion"].isin(estados_prioritarios)
    ].copy()

    columnas = [
        columna
        for columna in [
            "codigo_equipo",
            "nombre_equipo",
            "laboratorio",
            "frecuencia",
            "periodo",
            "ultima_verificacion",
            "fin_periodo",
            "dias_restantes_periodo",
            "estado_programacion",
        ]
        if columna in agenda.columns
    ]

    return agenda[columnas].head(limite).reset_index(drop=True)


def obtener_equipos_pendientes_periodo(limite=1000):
    programacion = obtener_proximas_verificaciones()

    if programacion.empty:
        return programacion

    pendientes = programacion[
        programacion["estado_programacion"].isin(
            {
                "🟡 Pendiente del período",
                "🔴 Vencido por intervalo",
                "🔴 Sin verificar",
            }
        )
    ].copy()

    columnas = [
        columna
        for columna in [
            "codigo_equipo",
            "nombre_equipo",
            "laboratorio",
            "frecuencia",
            "periodo",
            "ultima_verificacion",
            "fin_periodo",
            "dias_restantes_periodo",
            "estado_programacion",
        ]
        if columna in pendientes.columns
    ]

    return pendientes[columnas].head(limite).reset_index(drop=True)


def obtener_equipos_cumplidos_periodo(limite=1000):
    programacion = obtener_proximas_verificaciones()

    if programacion.empty:
        return programacion

    cumplidos = programacion[
        programacion["estado_programacion"].eq("🟢 Cumplido")
    ].copy()

    columnas = [
        columna
        for columna in [
            "codigo_equipo",
            "nombre_equipo",
            "laboratorio",
            "frecuencia",
            "periodo",
            "fecha_cumplimiento",
            "responsable_cumplimiento",
            "estado_programacion",
        ]
        if columna in cumplidos.columns
    ]

    return cumplidos[columnas].head(limite).reset_index(drop=True)


def obtener_cumplimiento_laboratorios():
    programacion = obtener_proximas_verificaciones()

    columnas = [
        "laboratorio",
        "programados",
        "cumplidos",
        "pendientes",
        "porcentaje_cumplimiento",
        "estado_laboratorio",
    ]

    if programacion.empty:
        return pd.DataFrame(columns=columnas)

    evaluables = programacion[
        ~programacion["estado_programacion"].eq("⚪ Sin frecuencia")
    ].copy()

    if evaluables.empty:
        return pd.DataFrame(columns=columnas)

    evaluables["cumplido"] = evaluables[
        "estado_programacion"
    ].eq("🟢 Cumplido")

    resumen = (
        evaluables.groupby("laboratorio", dropna=False)
        .agg(
            programados=("codigo_equipo", "size"),
            cumplidos=("cumplido", "sum"),
        )
        .reset_index()
    )
    resumen["cumplidos"] = resumen["cumplidos"].astype(int)
    resumen["pendientes"] = (
        resumen["programados"] - resumen["cumplidos"]
    )
    resumen["porcentaje_cumplimiento"] = (
        resumen["cumplidos"]
        / resumen["programados"]
        * 100
    ).round(1)
    resumen["estado_laboratorio"] = resumen.apply(
        lambda fila: (
            "🟢 100 % ejecutado"
            if fila["porcentaje_cumplimiento"] == 100
            else (
                "🟡 En ejecución"
                if fila["porcentaje_cumplimiento"] >= 70
                else "🔴 Requiere atención"
            )
        ),
        axis=1,
    )

    return resumen[columnas].sort_values(
        ["porcentaje_cumplimiento", "laboratorio"],
        ascending=[False, True],
    ).reset_index(drop=True)



def obtener_patrones_alerta(dias_alerta=30, limite=20):
    patrones = cargar_hoja("Equipos_Patrones")
    puntos = cargar_hoja("Puntos_Verificacion")
    equipos = _equipos()
    cols_out = ["codigo_patron","descripcion_patron","codigo_equipo","nombre_equipo","laboratorio","punto_verificacion","fecha_vencimiento","dias_restantes","estado_patron"]
    if patrones.empty: return pd.DataFrame(columns=cols_out)
    patrones = patrones.copy(); patrones.columns = [str(c).strip() for c in patrones.columns]
    cp = _buscar_columna(patrones, ["codigo_patron"])
    cv = _buscar_columna(patrones, ["fecha_vencimiento_calibracion","fecha_vencimiento","vencimiento"])
    cd = _buscar_columna(patrones, ["descripcion","nombre_patron"])
    if cp is None or cv is None: return pd.DataFrame(columns=cols_out)
    base = pd.DataFrame({
        "codigo_patron": patrones[cp].apply(_codigo),
        "descripcion_patron": patrones[cd].fillna("Patrón sin descripción").astype(str) if cd else "Patrón sin descripción",
        "fecha_vencimiento": pd.to_datetime(patrones[cv], errors="coerce", dayfirst=True),
    })
    hoy = pd.Timestamp(_ahora().date())
    base["dias_restantes"] = base["fecha_vencimiento"].dt.normalize().sub(hoy).dt.days
    base["estado_patron"] = base["dias_restantes"].apply(
        lambda d: "🔴 Vencido" if pd.notna(d) and d < 0 else ("🟡 Próximo a vencer" if pd.notna(d) and d <= dias_alerta else "🟢 Vigente"))
    base = base[base["estado_patron"].isin(["🔴 Vencido","🟡 Próximo a vencer"])]
    if base.empty: return pd.DataFrame(columns=cols_out)
    if not puntos.empty:
        puntos = puntos.copy(); puntos.columns = [str(c).strip() for c in puntos.columns]
        if "codigo_patron" in puntos.columns:
            puntos["codigo_patron"] = puntos["codigo_patron"].apply(_codigo)
            cols = [c for c in ["codigo_patron","codigo_equipo","punto_verificacion"] if c in puntos.columns]
            base = base.merge(puntos[cols].drop_duplicates(), on="codigo_patron", how="left")
    if "codigo_equipo" not in base.columns: base["codigo_equipo"] = ""
    base["codigo_equipo"] = base["codigo_equipo"].apply(_codigo)
    if not equipos.empty and "codigo_equipo" in equipos.columns:
        cols = [c for c in ["codigo_equipo","nombre_equipo","laboratorio"] if c in equipos.columns]
        base = base.merge(equipos[cols], on="codigo_equipo", how="left")
    for c in cols_out:
        if c not in base.columns: base[c] = ""
    return base.sort_values(["estado_patron","dias_restantes"]).head(limite)[cols_out].reset_index(drop=True)


def obtener_verificaciones_atencion(limite=20):
    sesiones = consultar_sesiones_verificacion(100000)
    cols = ["fecha","hora","id_sesion","codigo_equipo","nombre_equipo","laboratorio","responsable","estado_sesion","punto","resultado","limite_inferior","limite_superior","estado_punto","observacion"]
    if sesiones.empty or "estado" not in sesiones.columns: return pd.DataFrame(columns=cols)
    e = sesiones["estado"].astype(str).str.strip().str.lower()
    sesiones = sesiones[e.isin(["no conforme","incompleta"])]
    filas = []
    for _, s in sesiones.iterrows():
        d = consultar_detalle_sesion(s.get("id_sesion"))
        if d.empty:
            d = pd.DataFrame([{}])
        elif "estado_punto" in d.columns:
            ed = d["estado_punto"].astype(str).str.strip().str.lower()
            filtrado = d[ed.isin(["no cumple","no evaluado"])]
            if not filtrado.empty: d = filtrado
        for _, p in d.iterrows():
            filas.append({
                "fecha":s.get("fecha"), "hora":s.get("hora"), "id_sesion":s.get("id_sesion"),
                "codigo_equipo":s.get("codigo_equipo"), "nombre_equipo":s.get("nombre_equipo"),
                "laboratorio":s.get("laboratorio"), "responsable":s.get("responsable"),
                "estado_sesion":s.get("estado"), "punto":p.get("punto"), "resultado":p.get("resultado"),
                "limite_inferior":p.get("limite_inferior"), "limite_superior":p.get("limite_superior"),
                "estado_punto":p.get("estado_punto"), "observacion":p.get("observacion"),
            })
    if not filas: return pd.DataFrame(columns=cols)
    out = pd.DataFrame(filas)
    out["fecha_hora"] = pd.to_datetime(out["fecha"].astype(str)+" "+out["hora"].astype(str), errors="coerce")
    return out.sort_values("fecha_hora", ascending=False).head(limite)[cols].reset_index(drop=True)


def obtener_alertas(limite=8):
    alertas = []
    v = obtener_verificaciones_atencion(limite)
    for _, f in v.iterrows():
        estado = _txt(f.get("estado_sesion"), "Requiere atención")
        alertas.append({
            "nivel":"error" if estado.lower()=="no conforme" else "warning",
            "titulo":f"{_txt(f.get('codigo_equipo'),'Sin código')} · {_txt(f.get('nombre_equipo'),'Equipo sin nombre')}",
            "detalle":f"{estado}. Punto: {_txt(f.get('punto'),'Sin punto')}. Analista: {_txt(f.get('responsable'),'No registrado')}. Fecha: {_txt(f.get('fecha'),'Sin fecha')}.",
            "codigo_equipo":_txt(f.get("codigo_equipo")), "tipo":"Verificación",
        })
    if len(alertas) < limite:
        for _, f in obtener_patrones_alerta(30, limite-len(alertas)).iterrows():
            estado = _txt(f.get("estado_patron"))
            alertas.append({
                "nivel":"error" if "Vencido" in estado else "warning",
                "titulo":f"Patrón {_txt(f.get('codigo_patron'),'Sin código')} · {_txt(f.get('codigo_equipo'),'Equipo no relacionado')}",
                "detalle":f"{estado}. Vencimiento: {f.get('fecha_vencimiento')}. Días restantes: {f.get('dias_restantes')}.",
                "codigo_equipo":_txt(f.get("codigo_equipo")), "tipo":"Patrón",
            })
    return alertas[:limite]


def obtener_acciones_inmediatas(limite=15):
    filas = []
    for _, f in obtener_verificaciones_atencion(limite).iterrows():
        filas.append({"prioridad":1,"nivel":"🔴","tipo":"Verificación","codigo_equipo":f.get("codigo_equipo"),"nombre_equipo":f.get("nombre_equipo"),"laboratorio":f.get("laboratorio"),"motivo":f"{f.get('estado_sesion')} · Punto {f.get('punto')}","detalle":f"Resultado {f.get('resultado')} · LI {f.get('limite_inferior')} · LS {f.get('limite_superior')}","fecha":f.get("fecha"),"responsable":f.get("responsable")})
    for _, f in obtener_patrones_alerta(30, limite).iterrows():
        filas.append({"prioridad":1 if "Vencido" in _txt(f.get("estado_patron")) else 2,"nivel":"🔴" if "Vencido" in _txt(f.get("estado_patron")) else "🟡","tipo":"Patrón","codigo_equipo":f.get("codigo_equipo"),"nombre_equipo":f.get("nombre_equipo"),"laboratorio":f.get("laboratorio"),"motivo":f"{f.get('estado_patron')} · Patrón {f.get('codigo_patron')}","detalle":f"Vence: {f.get('fecha_vencimiento')} · Días: {f.get('dias_restantes')}","fecha":f.get("fecha_vencimiento"),"responsable":""})
    cal = _tabla("calibraciones", True)
    if not cal.empty:
        cal = cal[(cal.get("resultado","").isin(["Rechazada","Condicionada"])) | (cal.get("estado","").isin(["Vencida","Próxima a vencer"]))]
        for _, f in cal.iterrows():
            filas.append({"prioridad":1 if f.get("resultado")=="Rechazada" or f.get("estado")=="Vencida" else 2,"nivel":"🔴" if f.get("resultado")=="Rechazada" or f.get("estado")=="Vencida" else "🟡","tipo":"Calibración","codigo_equipo":f.get("codigo_equipo"),"nombre_equipo":"","laboratorio":"","motivo":f"{f.get('resultado') or f.get('estado')} · {f.get('numero_certificado') or 'Sin certificado'}","detalle":f"Próxima: {f.get('fecha_proxima_calibracion')}","fecha":f.get("fecha_calibracion"),"responsable":f.get("responsable")})
    mant = _tabla("mantenimientos", True)
    if not mant.empty and "resultado" in mant.columns:
        mant = mant[mant["resultado"].isin(["Equipo fuera de servicio","Requiere nueva intervención"])]
        for _, f in mant.iterrows():
            filas.append({"prioridad":1,"nivel":"🔴","tipo":"Mantenimiento","codigo_equipo":f.get("codigo_equipo"),"nombre_equipo":"","laboratorio":"","motivo":f.get("resultado"),"detalle":f.get("descripcion"),"fecha":f.get("fecha_inicio"),"responsable":f.get("responsable")})
    if not filas: return pd.DataFrame(columns=["nivel","tipo","codigo_equipo","nombre_equipo","laboratorio","motivo","detalle","fecha","responsable"])
    return pd.DataFrame(filas).sort_values(["prioridad","fecha"], ascending=[True,False], na_position="last").drop(columns=["prioridad"]).head(limite).reset_index(drop=True)


def obtener_estado_general():
    a = obtener_acciones_inmediatas(50)
    if a.empty:
        return {"nivel":"success","estado":"Operación controlada","detalle":"No se identifican acciones inmediatas en este momento."}
    criticas = int(a["nivel"].astype(str).eq("🔴").sum())
    if criticas:
        equipos = ", ".join(a.head(3)["codigo_equipo"].fillna("Sin código").astype(str).tolist())
        return {"nivel":"error","estado":"Acción inmediata","detalle":f"{criticas} situación(es) crítica(s). Equipos prioritarios: {equipos}."}
    return {"nivel":"warning","estado":"Requiere atención","detalle":f"{len(a)} situación(es) requieren seguimiento."}


def obtener_indice_salud():
    k = obtener_kpis(); p = obtener_resumen_programacion()
    te = max(k["equipos"],1); ts = max(k["verificaciones"],1)
    indice = (k["activos"]/te*30 + k["porcentaje_conformidad"]/100*35 + p["vigentes"]/te*35 - (p["vencidas"]+p["sin_verificar"]+p["proximas"]*0.35)/te*20 - (k["no_conformes"]+k["incompletas"]*0.5)/ts*15)
    indice = max(0.0,min(100.0,round(indice,1)))
    if indice>=90: nivel,estado="Excelente","🟢"
    elif indice>=75: nivel,estado="Bueno","🟢"
    elif indice>=60: nivel,estado="Aceptable","🟡"
    elif indice>=40: nivel,estado="En riesgo","🟠"
    else: nivel,estado="Crítico","🔴"
    return {"indice":indice,"nivel":nivel,"estado":estado}


def obtener_tendencia_mensual():
    s = consultar_sesiones_verificacion(100000)
    cols=["mes","verificaciones","conformes","no_conformes"]
    if s.empty or "fecha" not in s.columns: return pd.DataFrame(columns=cols)
    s=s.copy(); s["fecha"]=pd.to_datetime(s["fecha"], errors="coerce", dayfirst=True); s=s.dropna(subset=["fecha"])
    if s.empty: return pd.DataFrame(columns=cols)
    s["mes_periodo"]=s["fecha"].dt.to_period("M"); s["estado_normalizado"]=s.get("estado","").astype(str).str.strip().str.lower()
    r=s.groupby("mes_periodo").agg(verificaciones=("fecha","size"),conformes=("estado_normalizado",lambda x:int((x=="conforme").sum())),no_conformes=("estado_normalizado",lambda x:int((x=="no conforme").sum()))).reset_index().sort_values("mes_periodo")
    r["mes"]=r["mes_periodo"].dt.strftime("%Y-%m")
    return r[cols].tail(12).reset_index(drop=True)


def obtener_ranking_equipos(limite=10):
    s=consultar_sesiones_verificacion(100000)
    cols=["codigo_equipo","nombre_equipo","laboratorio","verificaciones"]
    if s.empty or "codigo_equipo" not in s.columns: return pd.DataFrame(columns=cols)
    grupos=["codigo_equipo"]+[c for c in ["nombre_equipo","laboratorio"] if c in s.columns]
    r=s.groupby(grupos, dropna=False).size().reset_index(name="verificaciones").sort_values("verificaciones", ascending=False).head(limite)
    for c in cols:
        if c not in r.columns: r[c]=""
    return r[cols].reset_index(drop=True)