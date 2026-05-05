import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns   
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json

conn = st.connection("sqlserver", type="sql")

@st.cache_data(ttl=600)
def load_data_encabezado():
    return conn.query("""SELECT  [NumOrdFab]
      ,[Status]
      ,[Fecha]
      ,[StartDate]
      ,[DueDate]
      ,[CloseDate]
      ,[CodPT]
      ,[NamPT]
      ,[PlannedQty]
      ,[CmpltQty]
      ,[CodMP]
      ,[NamMP]
      ,[Requerido]
      ,[Consumido]
  FROM [SBO_HELA].[dbo].[Z_VIEW_ORDEN_DE_FABRICACION_HISTORICO]
  WHERE Status in ('P','R') """)

@st.cache_data(ttl=600)
def load_data_detalle():
    return conn.query("""SELECT        
    TOP (100) PERCENT T0.DocNum AS [N° OF], 
    T0.DueDate AS FechaTermino, 
    T0.ItemCode AS [Cod. PT], 
    T0.ProdName AS [Nombre Padre], 
    CONVERT(VARCHAR,T0.PlannedQty) AS Planificado, 
    CONVERT(VARCHAR,T0.CmpltQty) AS Completado, 
    T1.ItemCode AS [Cod. MP], 
    T2.ItemName AS [Nombre MP], 
    CONVERT(VARCHAR,T1.PlannedQty) AS [Cant. Neces.]
    ,ISNULL(T4.CardName, '') AS Cliente
FROM            
    dbo.OWOR AS T0 
    INNER JOIN dbo.WOR1 AS T1 ON T0.DocEntry = T1.DocEntry 
    INNER JOIN dbo.OITM AS T2 ON T1.ItemCode = T2.ItemCode 
    LEFT OUTER JOIN dbo.IGE1 AS T3 ON T0.DocEntry = T3.BaseEntry AND T1.LineNum = T3.BaseLine
    LEFT OUTER JOIN dbo.OCRD AS T4 ON (T0.CardCode = T4.CardCode)
WHERE        
    (YEAR(T0.PostDate) >= 2023) AND (T0.CloseDate IS NULL) and T0.Status in ('P','R')
ORDER BY 
    T0.DocNum DESC""")

@st.cache_data(ttl=600)
def load_data_activa():
    return conn.query("""SELECT [NumOrdFab]
      ,[STATUS]
      ,[TIPO DE ORD FAB]
      ,[FECHA DOCUMENTO]
      ,[FECHA CREACIÓN]
      ,[FECHA INICIO]
      ,[FECHA TERMINO]
      ,[Codigo PT]
      ,[Nombre Prod Terminado]
      ,[Cant Planificada]
      ,[Cant Completada]
      ,[Codigo MP]
      ,[Nombre MP]
      ,[Requerido]
      ,[Completado]
      ,[RjctQty]
      ,[Consumido]
      ,[OriginAbs]
      ,[OriginNum]
      ,[CardCode]
      ,[Cliente]
      ,[TIPO DE ORD DE FAB]
  FROM [SBO_HELA].[dbo].[Z_VIEW_ORDEN_FABRICACION_ACTIVA_FORM]""")

df_ordenes_encabezado = load_data_encabezado().copy()
df_ordenes = load_data_detalle().copy()
df_orden_activa = load_data_activa().copy()

# Formatear fechas
for col in ['Fecha', 'StartDate', 'DueDate', 'CloseDate']:
    if col in df_ordenes_encabezado.columns:
        df_ordenes_encabezado[col] = pd.to_datetime(df_ordenes_encabezado[col], errors='coerce').dt.strftime('%d-%m-%Y')

if 'FechaTermino' in df_ordenes.columns:
    df_ordenes['FechaTermino'] = pd.to_datetime(df_ordenes['FechaTermino'], errors='coerce').dt.strftime('%d-%m-%Y')

for col in ['FECHA DOCUMENTO', 'FECHA CREACIÓN', 'FECHA INICIO', 'FECHA TERMINO']:
    if col in df_orden_activa.columns:
        df_orden_activa[col] = pd.to_datetime(df_orden_activa[col], errors='coerce').dt.strftime('%d-%m-%Y')

@st.dialog("📋 Detalle de Orden de Fabricación", width="large")
def show_order_modal(of_num):
    detalle = df_orden_activa[df_orden_activa['NumOrdFab'].astype(str) == str(of_num)]
    
    if detalle.empty:
        st.error(f"❌ No se encontró información para la Orden: **{of_num}**")
        return

    # Encabezado Premium
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0c2836 0%, #185675 100%); padding: 20px; border-radius: 12px; margin-bottom: 25px; border-left: 5px solid #2bb9c8; color: white;">
            <h2 style="margin: 0; color: white;">Orden de Fabricación N° {of_num}</h2>
            <p style="color: #2bb9c8; margin: 8px 0 0 0; font-weight: bold; font-size: 16px;">{detalle['Nombre Prod Terminado'].iloc[0]}</p>
        </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Estado", detalle['STATUS'].iloc[0])
    with m2: st.metric("Planificado", f"{detalle['Cant Planificada'].iloc[0]:,.0f}")
    with m3: st.metric("Completado", f"{detalle['Cant Completada'].iloc[0]:,.0f}")
    with m4: st.metric("Cliente", detalle['Cliente'].iloc[0] or "N/A")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ℹ️ Información")
        st.write(f"**Código PT:** `{detalle['Codigo PT'].iloc[0]}`")
        st.write(f"**Tipo OF:** {detalle['TIPO DE ORD FAB'].iloc[0]}")
    with c2:
        st.markdown("### 📅 Cronograma")
        st.write(f"**Inicio:** {detalle['FECHA INICIO'].iloc[0]}")
        st.write(f"**Término:** {detalle['FECHA TERMINO'].iloc[0]}")

    st.markdown("### 📦 Insumos")
    st.dataframe(detalle[['Codigo MP', 'Nombre MP', 'Requerido', 'Consumido', 'Completado', 'RjctQty']], use_container_width=True, hide_index=True)
    
    if st.button("Cerrar Detalle", use_container_width=True):
        st.query_params.clear()
        st.rerun()

# Control de activación del modal
if "modal_of" in st.query_params:
    # Extraer el valor
    of_num = st.query_params["modal_of"]
    # Limpiar la URL INMEDIATAMENTE para que al recargar (F5) no vuelva a abrirse
    del st.query_params["modal_of"]
    # Mostrar el modal (st.dialog lo mantendrá abierto en el frontend)
    show_order_modal(of_num)

# custom styles
st.markdown("""
<style>
.color1 {color: #060606;}
.color2 {color: #0c2836;}
.color3 {color: #185675;}
.color4 {color: #2689bd;}
.color5 {color: #2bb9c8;}

.stMetric {
    border:1px solid #ccc;
    padding:10px 20px;
    border-radius:8px;
    box-shadow:0 2px 4px rgba(0,0,0,0.1);
    margin-bottom:10px;
}
.stMetric .stMetricValue { font-size: 1rem !important; }
.stMetric .stMetricLabel { font-size: 0.85rem !important; }

h1 {font-size:24px !important;}
h2 {font-size:20px !important;}
h3 {font-size:18px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("# Informe de Producción")
st.write("Listado de órdenes de fabricación activas (P o R)")
st.markdown("---")

df_ordenes_encabezado_filtered = df_ordenes_encabezado.copy()
df_filtered = df_ordenes.copy()

# Contenedor para el botón de exportar (aparecerá arriba)
export_container = st.container()

# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN: ÓRDENES POR ESTADO (R y P)
# ──────────────────────────────────────────────────────────────────────────────
def render_status_section(df_base, status_code, status_name):
    st.markdown(f"### 📋 Órdenes en Estado: {status_name} ({status_code})")
    
    # Filtrar por status
    df_st = df_base[df_base['Status'] == status_code].copy()
    
    # Filtros de la sección
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c1:
        f_codpt = st.text_input(f"🔍 CodPT", key=f"f_codpt_{status_code}", placeholder="Código...")
    with c2:
        f_nampt = st.text_input(f"🔍 NamPT", key=f"f_nampt_{status_code}", placeholder="Nombre...")
    with c3:
        st.write("") # Espaciador
        st.write("")
        show_overdue = st.toggle("🕒 Solo Vencidas (DueDate < Hoy)", key=f"overdue_{status_code}")

    # Aplicar filtros
    if f_codpt:
        df_st = df_st[df_st['CodPT'].astype(str).str.contains(f_codpt, case=False, na=False)]
    if f_nampt:
        df_st = df_st[df_st['NamPT'].astype(str).str.contains(f_nampt, case=False, na=False)]
    
    if show_overdue:
        # Convertir DueDate a datetime para comparar
        # Intentamos parsear considerando que el formato previo puede ser str DD-MM-YYYY o datetime
        # DueDate ya fue formateada como string DD-MM-YYYY en el pre-procesamiento
        df_st['DueDate_DT'] = pd.to_datetime(df_st['DueDate'], format='%d-%m-%Y', errors='coerce')
        hoy = pd.Timestamp.today().normalize()
        df_st = df_st[df_st['DueDate_DT'] < hoy]

    # Columnas a mostrar (sin datos de MP para esta vista)
    cols_view = ['NumOrdFab', 'Status', 'Fecha', 'StartDate', 'DueDate', 'CodPT', 'NamPT', 'PlannedQty', 'CmpltQty']
    df_st_unique = df_st[cols_view].drop_duplicates('NumOrdFab')

    if not df_st_unique.empty:
        st.dataframe(df_st_unique, use_container_width=True, hide_index=True)
    else:
        st.info(f"No se encontraron órdenes '{status_name}' con los filtros aplicados.")

# Renderizar secciones
render_status_section(df_ordenes_encabezado, 'R', 'Liberadas')
st.markdown("<br>", unsafe_allow_html=True)
render_status_section(df_ordenes_encabezado, 'P', 'Planificadas')

st.markdown("---")



st.subheader("Consolidado de Materia Prima")
    
# Selectores y Buscadores para el consolidado
col_f1, col_f2 = st.columns(2)

with col_f1:
    ofs_disponibles = df_filtered['N° OF'].astype(str).unique().tolist()
    selected_ofs = st.multiselect(
        "🔍 Filtrar por N° OF:",
        options=ofs_disponibles,
        default=[]
    )
    
with col_f2:
    search_mp = st.text_input(
        "🔍 Buscar Código o Nombre MP:", 
        placeholder="Ej: AZUCAR, 100234..."
    )

# Preparar el dataframe consolidadomp
df_filtered_calc = df_filtered.copy()
df_filtered_calc['N° OF STR'] = df_filtered_calc['N° OF'].astype(str)

# Filtrar por OFs si el usuario seleccionó alguna
if selected_ofs:
    df_filtered_calc = df_filtered_calc[df_filtered_calc['N° OF STR'].isin(selected_ofs)]
    
# Filtrar por búsqueda de texto de MP si se ingresó algo
if search_mp:
    term = search_mp.strip()
    mask_cod = df_filtered_calc['Cod. MP'].astype(str).str.contains(term, case=False, na=False)
    mask_name = df_filtered_calc['Nombre MP'].astype(str).str.contains(term, case=False, na=False)
    df_filtered_calc = df_filtered_calc[mask_cod | mask_name]
    
df_filtered_calc['Cant. Neces. Num'] = pd.to_numeric(df_filtered_calc['Cant. Neces.'], errors='coerce').fillna(0)

consolidadomp = df_filtered_calc.groupby(['Cod. MP', 'Nombre MP']).agg(
    Cant_Neces_Total=('Cant. Neces. Num', 'sum'),
    Lista_OF=('N° OF', lambda x: list(set(x)))
).reset_index()

def render_of_buttons(of_list):
    html_str = ""
    for of_num in of_list:
        # Volver a usar enlaces de Streamlit para activar el st.dialog mediante parámetros de consulta
        html_str += f'<a href="?modal_of={of_num}" target="_self" style="text-decoration: none; padding: 4px 10px; margin: 2px; background-color: #2689bd; color: white; border-radius: 4px; font-size: 12px; display: inline-block;">OF {of_num}</a>'
    return html_str
    
consolidadomp_show = consolidadomp.copy()
if not consolidadomp_show.empty:
    consolidadomp_show['Cant. Neces. Total'] = consolidadomp_show['Cant_Neces_Total'].apply(lambda x: f"{x:,.2f}")
    consolidadomp_show['Órdenes Asociadas (Clic para Detalles)'] = consolidadomp_show['Lista_OF'].apply(render_of_buttons)
    consolidadomp_show = consolidadomp_show[['Cod. MP', 'Nombre MP', 'Cant. Neces. Total', 'Órdenes Asociadas (Clic para Detalles)']]

# Renderizamos como HTML puro envuelto en un div con scroll (altura máxima definida)
if not consolidadomp_show.empty:
    html_table = consolidadomp_show.to_html(escape=False, index=False)
    st.markdown(f"<div style='max-height: 450px; overflow-y: auto; overflow-x: hidden !important; border: 1px solid #444; border-radius: 6px;'>{html_table}</div>", unsafe_allow_html=True)
else:
    st.info("No hay datos para consolidar con los filtros seleccionados.")

# Estilos CSS de tabla para integrarla visualmente al theme de Streamlit
st.markdown("""
<style>
table { width: 100%; border-collapse: collapse; margin-top: 0px; font-size: 14px;}
th { background-color: #0c2836; color: white; padding: 10px; text-align: left; position: sticky; top: 0; z-index: 1;}
td { padding: 8px; border-bottom: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# Lógica del botón de exportación inyectada en el contenedor superior
with export_container:
    import io
    col_export1, col_export2 = st.columns([5, 1])
    with col_export2:
        try:
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_ordenes_encabezado_filtered.to_excel(writer, sheet_name='Encabezado', index=False)
                df_filtered.to_excel(writer, sheet_name='Detalle', index=False)
            
            st.download_button(
                label="📥 Exportar a Excel",
                data=buf.getvalue(),
                file_name="Ordenes_Exportacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            st.error("⚠️ Falta instalar 'openpyxl'. Por favor, en tu terminal ejecuta: pip install openpyxl")


