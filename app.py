import streamlit as st
import plotly.express as px

from config import APP_NAME
from database import crear_base_datos
from utils.data import cargar_hoja
from utils.ui import aplicar_estilo, encabezado, login_limpio, pie_pagina, sidebar_pro
from utils.dashboard import (
    obtener_acciones_inmediatas, obtener_agenda_critica, obtener_alertas,
    obtener_bitacora_reciente, obtener_equipos_por_laboratorio,
    obtener_estado_general, obtener_estado_verificaciones, obtener_indice_salud,
    obtener_kpis, obtener_patrones_alerta, obtener_ranking_equipos,
    obtener_resumen_programacion, obtener_tendencia_mensual,
    obtener_ultimas_verificaciones, obtener_verificaciones_atencion,
    obtener_equipos_pendientes_periodo, obtener_equipos_cumplidos_periodo,
    obtener_cumplimiento_laboratorios,
)

st.set_page_config(page_title=APP_NAME, page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
aplicar_estilo(); crear_base_datos()

st.markdown("""
<style>
.pc-title{font-size:24px;font-weight:800;line-height:1.2;color:#0f2747;margin-bottom:.4rem}
.pc-sub{font-size:13px;line-height:1.4;color:#506784;margin-bottom:.7rem}
.pc-alert{border:1px solid #cbd8e8;border-left:4px solid #147a3b;border-radius:10px;padding:.65rem .75rem;margin-bottom:.5rem;background:#fff}
.pc-alert.error{border-left-color:#c62828}.pc-alert.warning{border-left-color:#d97706}
.pc-alert-title{font-size:14px;font-weight:800;line-height:1.25;color:#0f2747;overflow-wrap:anywhere}
.pc-alert-detail{font-size:12px;line-height:1.4;color:#445b78;overflow-wrap:anywhere}
div[data-testid="stMetricValue"]{font-size:25px;line-height:1.1}
div[data-testid="stMetricLabel"]{font-size:12px}div[data-testid="stMetricDelta"]{font-size:11px}
div[data-testid="stDataFrame"]{font-size:11px}
h3{font-size:18px!important;line-height:1.25!important}
</style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
if not st.session_state["autenticado"]:
    encabezado(); _, c, _ = st.columns([1,1.15,1])
    with c: login_limpio()
    st.stop()
sidebar_pro(); encabezado()

def abrir_equipo(codigo):
    equipos=cargar_hoja("Equipos")
    if equipos.empty or "codigo_equipo" not in equipos.columns:
        st.error("No fue posible cargar el catálogo de equipos."); return
    def norm(v):
        t=str(v or "").strip(); return t[:-2] if t.endswith(".0") and t[:-2].replace("-","").isdigit() else t
    equipos=equipos.copy(); equipos["_codigo"]=equipos["codigo_equipo"].apply(norm)
    fila=equipos[equipos["_codigo"].eq(norm(codigo))]
    if fila.empty: st.error(f"No se encontró el equipo {codigo}."); return
    st.session_state["equipo_seleccionado"]=fila.iloc[0].drop(labels=["_codigo"],errors="ignore").to_dict()
    st.switch_page("pages/02_Hoja_de_Vida.py")

kpis=obtener_kpis(); estado_verificaciones=obtener_estado_verificaciones(); equipos_lab=obtener_equipos_por_laboratorio()
ultimas=obtener_ultimas_verificaciones(8); actividad=obtener_bitacora_reciente(12); alertas=obtener_alertas(8)
estado_general=obtener_estado_general(); resumen=obtener_resumen_programacion(); salud=obtener_indice_salud()
agenda=obtener_agenda_critica(20); tendencia=obtener_tendencia_mensual(); ranking=obtener_ranking_equipos(8)
acciones=obtener_acciones_inmediatas(15); patrones=obtener_patrones_alerta(30,20); no_conformes=obtener_verificaciones_atencion(20)
pendientes_periodo=obtener_equipos_pendientes_periodo(1000)
cumplidos_periodo=obtener_equipos_cumplidos_periodo(1000)
cumplimiento_laboratorios=obtener_cumplimiento_laboratorios()

st.markdown('<div class="pc-title">Centro de control</div>', unsafe_allow_html=True)
st.markdown('<div class="pc-sub">Resumen operativo de equipos, verificaciones, patrones, programación y eventos que requieren atención.</div>', unsafe_allow_html=True)

c1,c2=st.columns([1,1.75])
with c1:
    with st.container(border=True):
        st.markdown("### 💓 Salud del laboratorio"); st.metric("Índice general",f'{salud["indice"]:.1f} %',delta=f'{salud["estado"]} {salud["nivel"]}'); st.progress(salud["indice"]/100)
with c2:
    mensaje=f'### {"🔴" if estado_general["nivel"]=="error" else "🟡" if estado_general["nivel"]=="warning" else "🟢"} {estado_general["estado"]}\n\n{estado_general["detalle"]}'
    (st.error if estado_general["nivel"]=="error" else st.warning if estado_general["nivel"]=="warning" else st.success)(mensaje)

m1,m2,m3,m4=st.columns(4)
m1.metric("🧪 Equipos registrados",kpis["equipos"],delta=f'{kpis["activos"]} activos')
m2.metric("📋 Verificaciones",kpis["verificaciones"],delta=f'{kpis["conformes"]} conformes')
m3.metric("🛡️ Conformidad",f'{kpis["porcentaje_conformidad"]:.1f} %')
m4.metric("🔔 Alertas",kpis["alertas"],delta=f'{kpis["no_conformes"]} no conformes · {kpis["incompletas"]} incompletas',delta_color="inverse")

st.divider(); st.markdown("### 🚨 Acciones inmediatas")
if acciones.empty: st.success("No existen acciones inmediatas pendientes.")
else:
    a,b=st.columns([3.8,1])
    with a: st.dataframe(acciones,width="stretch",hide_index=True,height=min(430,38+len(acciones)*35))
    with b:
        codigos=acciones["codigo_equipo"].dropna().astype(str); codigos=codigos[(codigos.str.strip()!="")&(codigos.str.lower()!="equipo no relacionado")].drop_duplicates().tolist()
        if codigos:
            sel=st.selectbox("Abrir equipo",codigos,key="dash_accion")
            if st.button("📘 Ver Hoja de Vida",width="stretch",type="primary"): abrir_equipo(sel)

st.divider()
st.markdown("### 📅 Cumplimiento del programa por período")

periodo_referencia = (
    pendientes_periodo["periodo"].dropna().astype(str).iloc[0]
    if not pendientes_periodo.empty
    else (
        cumplidos_periodo["periodo"].dropna().astype(str).iloc[0]
        if not cumplidos_periodo.empty
        else "Período actual"
    )
)

pr1, pr2, pr3, pr4 = st.columns(4)
pr1.metric("Equipos programados", resumen["programados"])
pr2.metric("✅ Cumplidos", resumen["cumplidos"])
pr3.metric("⏳ Pendientes", resumen["pendientes"] + resumen["sin_verificar"] + resumen["vencidos_intervalo"])
pr4.metric(
    "Cumplimiento global",
    f'{resumen["porcentaje_cumplimiento"]:.1f} %',
    delta=periodo_referencia,
)

st.progress(
    min(max(resumen["porcentaje_cumplimiento"] / 100, 0.0), 1.0)
)

tab_pendientes, tab_cumplidos, tab_laboratorios = st.tabs(
    [
        "⏳ Equipos pendientes",
        "✅ Equipos cumplidos",
        "🏭 Cumplimiento por laboratorio",
    ]
)

with tab_pendientes:
    st.caption(
        "Equipos que todavía no tienen una verificación registrada "
        "dentro del período que corresponde a su frecuencia."
    )
    if pendientes_periodo.empty:
        st.success("Todos los equipos programados cumplieron el período.")
    else:
        st.dataframe(
            pendientes_periodo,
            width="stretch",
            hide_index=True,
            height=min(430, 38 + len(pendientes_periodo) * 35),
        )

with tab_cumplidos:
    st.caption(
        "Equipos que ya cuentan con al menos una verificación válida "
        "dentro del período calendario actual."
    )
    if cumplidos_periodo.empty:
        st.info("Todavía no hay equipos cumplidos en el período.")
    else:
        st.dataframe(
            cumplidos_periodo,
            width="stretch",
            hide_index=True,
            height=min(430, 38 + len(cumplidos_periodo) * 35),
        )

with tab_laboratorios:
    st.caption(
        "El laboratorio alcanza 100 % cuando todos sus equipos "
        "programados han sido verificados dentro del período."
    )
    if cumplimiento_laboratorios.empty:
        st.info("No hay información suficiente por laboratorio.")
    else:
        st.dataframe(
            cumplimiento_laboratorios,
            width="stretch",
            hide_index=True,
            height=min(430, 38 + len(cumplimiento_laboratorios) * 35),
            column_config={
                "porcentaje_cumplimiento": st.column_config.ProgressColumn(
                    "Cumplimiento",
                    min_value=0,
                    max_value=100,
                    format="%.1f %%",
                )
            },
        )

st.markdown("#### Equipos que requieren atención en el período")
if agenda.empty:
    st.success("No hay equipos pendientes del programa.")
else:
    st.dataframe(
        agenda,
        width="stretch",
        hide_index=True,
        height=min(430, 38 + len(agenda) * 35),
    )

st.divider(); p1,p2=st.columns([1,1.25])
with p1:
    st.markdown("### ⚖️ Patrones vencidos o próximos")
    if patrones.empty:
        st.success("No hay patrones vencidos ni próximos a vencer.")
    else:
        columnas_patrones = [
            columna
            for columna in [
                "codigo_patron",
                "descripcion_patron",
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "fecha_vencimiento",
                "dias_restantes",
                "estado_patron",
            ]
            if columna in patrones.columns
        ]
        st.dataframe(
            patrones[columnas_patrones],
            width="stretch",
            hide_index=True,
            height=min(430, 38 + len(patrones) * 35),
        )
with p2:
    st.markdown("### ⚠️ Verificaciones no conformes")
    if no_conformes.empty:
        st.success(
            "No hay verificaciones no conformes o incompletas."
        )
    else:
        columnas_no_conformes = [
            columna
            for columna in [
                "fecha",
                "hora",
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "estado_sesion",
                "punto",
                "resultado",
                "limite_inferior",
                "limite_superior",
                "estado_punto",
                "responsable",
                "observacion",
            ]
            if columna in no_conformes.columns
        ]
        st.dataframe(
            no_conformes[columnas_no_conformes],
            width="stretch",
            hide_index=True,
            height=min(430, 38 + len(no_conformes) * 35),
        )

st.divider(); g1,g2=st.columns([1,1.25])
with g1:
    st.markdown("### Estado de verificaciones")
    if estado_verificaciones.empty: st.info("Aún no hay verificaciones registradas.")
    else:
        fig=px.pie(estado_verificaciones,names="estado",values="cantidad",hole=.58,color="estado",color_discrete_map={"Conforme":"#147A3B","No conforme":"#C62828","Incompleta":"#D97706"})
        fig.update_traces(textposition="inside",textinfo="percent+label",textfont_size=11); fig.update_layout(height=340,margin=dict(l=10,r=10,t=10,b=10),font=dict(size=11)); st.plotly_chart(fig,width="stretch")
with g2:
    st.markdown("### Equipos por laboratorio")
    if equipos_lab.empty: st.info("No hay información de laboratorios.")
    else:
        fig=px.bar(equipos_lab,x="laboratorio",y="cantidad",text="cantidad"); fig.update_traces(marker_color="#0759C7",textposition="outside",textfont_size=11); fig.update_layout(height=340,margin=dict(l=10,r=10,t=10,b=10),font=dict(size=11),showlegend=False); st.plotly_chart(fig,width="stretch")

st.divider(); t1,t2=st.columns([1.25,1])
with t1:
    st.markdown("### Tendencia mensual")
    if tendencia.empty: st.info("Aún no hay información mensual suficiente.")
    else:
        fig=px.line(tendencia,x="mes",y="verificaciones",markers=True); fig.update_traces(line_color="#0759C7",marker_color="#147A3B"); fig.update_layout(height=330,margin=dict(l=10,r=10,t=10,b=10),font=dict(size=11),showlegend=False); st.plotly_chart(fig,width="stretch")
with t2:
    st.markdown("### Alertas y atención")
    if not alertas: st.success("No existen alertas operativas.")
    else:
        for i,a in enumerate(alertas):
            clase="error" if a["nivel"]=="error" else "warning"
            st.markdown(f'<div class="pc-alert {clase}"><div class="pc-alert-title">{a["titulo"]}</div><div class="pc-alert-detail">{a["detalle"]}</div></div>',unsafe_allow_html=True)
            cod=str(a.get("codigo_equipo","")).strip()
            if cod and cod.lower()!="equipo no relacionado" and st.button("Abrir equipo",key=f"abrir_alerta_{i}",width="stretch"): abrir_equipo(cod)

st.divider(); u1,u2=st.columns([1.3,1])
with u1:
    st.markdown("### Últimas verificaciones")
    if ultimas.empty:
        st.info("Aún no existen sesiones registradas.")
    else:
        columnas_ultimas = [
            columna
            for columna in [
                "fecha",
                "hora",
                "codigo_equipo",
                "nombre_equipo",
                "laboratorio",
                "responsable",
                "estado",
                "total_puntos",
            ]
            if columna in ultimas.columns
        ]
        st.dataframe(
            ultimas[columnas_ultimas],
            width="stretch",
            hide_index=True,
        )
with u2:
    st.markdown("### Actividad reciente")
    if actividad.empty:
        st.info("La bitácora todavía no tiene eventos.")
    else:
        columnas_actividad = [
            columna
            for columna in [
                "fecha",
                "hora",
                "codigo_equipo",
                "categoria",
                "evento",
                "usuario",
                "estado",
            ]
            if columna in actividad.columns
        ]
        st.dataframe(
            actividad[columnas_actividad],
            width="stretch",
            hide_index=True,
        )

st.divider(); st.markdown("### Equipos con mayor actividad")
if ranking.empty: st.info("Aún no hay información para construir el ranking.")
else:
    fig=px.bar(ranking.sort_values("verificaciones"),x="verificaciones",y="codigo_equipo",orientation="h",text="verificaciones",hover_data=[c for c in ["nombre_equipo","laboratorio"] if c in ranking.columns]); fig.update_traces(marker_color="#147A3B",textfont_size=11); fig.update_layout(height=340,margin=dict(l=10,r=10,t=10,b=10),font=dict(size=11),showlegend=False); st.plotly_chart(fig,width="stretch")
pie_pagina()