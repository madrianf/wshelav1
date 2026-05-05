import streamlit as st
import pandas as pd

# Conexión principal de base de datos SQL Server
conn = st.connection("sqlserver", type="sql")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* Estilo para las métricas */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8ecf1;
        border-radius: 14px;
        padding: 20px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Contenedor para gráficos con simetría */
    .chart-container {
        border: 1px solid #e8ecf1;
        border-radius: 14px;
        padding: 20px;
        background: #ffffff;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# --- CARGA DE DATOS CON CACHÉ ---

@st.cache_data
def get_data_infull():
    return conn.query("""SELECT  [fechapedido]
      ,[numpedido]
      ,[cantpedida]
      ,[cantentregada]
      ,[Indicador]
  FROM [SBO_HELA].[dbo].[Z_VIEW_KPI_INFULL]""")

@st.cache_data
def get_data_ontime():
    return conn.query("""SELECT  [numpedido]
      ,[fechapedido]
      ,[fechaentrega]
      ,[Indicador]
  FROM [SBO_HELA].[dbo].[Z_VIEW_KPI_ONTIME]""")

# Ejecución de la carga de datos
df_infull = get_data_infull()
df_ontime = get_data_ontime()

# --- CONSOLIDACIÓN OTIF (On-Time In-Full) ---
# Se une In-Full y On-Time por número de pedido para calcular OTIF
df_otif = pd.merge(
    df_infull[['numpedido', 'fechapedido', 'Indicador']].rename(columns={'Indicador': 'InFull'}),
    df_ontime[['numpedido', 'Indicador']].rename(columns={'Indicador': 'OnTime'}),
    on='numpedido',
    how='inner'
)

df_otif['OTIF'] = df_otif.apply(
    lambda x: 'CUMPLE' if (x['InFull'] == 'CUMPLE' and x['OnTime'] == 'CUMPLE') else 'NO CUMPLE',
    axis=1
)

# Función para resaltar "NO CUMPLE" en rojo
def highlight_no_cumple(val):
    if val == "NO CUMPLE":
        return 'color: red; font-weight: bold'
    return ''

# --- DASHBOARD UI ---
st.markdown("## Dashboard Logística")

# --- SECCIÓN 1: OTIF (Prioridad) ---
st.markdown("---")
st.subheader("🎯 Análisis OTIF (On-Time In-Full)")

# --- FILTROS GLOBALES ---
_hoy = pd.Timestamp.today()
_inicio_mes = _hoy.replace(day=1)

rango_fecha = st.date_input(
    "Seleccione Rango de Fechas (fechapedido):",
    value=(_inicio_mes.date(), _hoy.date()),
    key="filtro_fechas_global"
)

# Aplicar filtros a todos los dataframes
if isinstance(rango_fecha, (list, tuple)) and len(rango_fecha) == 2:
    start_f, end_f = pd.to_datetime(rango_fecha[0]), pd.to_datetime(rango_fecha[1])

    # 1. Filtro In-Full
    df_infull['fechapedido'] = pd.to_datetime(df_infull['fechapedido'], errors='coerce')
    df_filt = df_infull[(df_infull['fechapedido'] >= start_f) & (df_infull['fechapedido'] <= end_f)].copy()

    # 2. Filtro On-Time
    df_ontime['fechapedido'] = pd.to_datetime(df_ontime['fechapedido'], errors='coerce')
    df_filt_ot = df_ontime[(df_ontime['fechapedido'] >= start_f) & (df_ontime['fechapedido'] <= end_f)].copy()

    # 3. Filtro OTIF (usa fechapedido proveniente del merge con infull)
    df_otif['fechapedido'] = pd.to_datetime(df_otif['fechapedido'], errors='coerce')
    df_filt_otif = df_otif[(df_otif['fechapedido'] >= start_f) & (df_otif['fechapedido'] <= end_f)].copy()

   
    # Visualización OTIF
    col_m3, col_g3 = st.columns([2, 4])
    total_otif = len(df_filt_otif)
    cumplen_otif = (df_filt_otif['OTIF'] == 'CUMPLE').sum()
    pct_otif = (cumplen_otif / total_otif * 100) if total_otif > 0 else 0
    with col_m3:
        st.metric(label="🎯 Índice OTIF", value=f"{pct_otif:.1f}%", delta=f"{cumplen_otif} de {total_otif} pedidos")
    with col_g3:
        if not df_filt_otif.empty:
            df_evolucion_otif = df_filt_otif[df_filt_otif['OTIF'] == 'CUMPLE'].groupby('fechapedido').size().reset_index(name='Cant_Pedidos')
            st.line_chart(df_evolucion_otif.set_index('fechapedido')['Cant_Pedidos'], height=200)
        else:
            st.info("Sin datos para OTIF en el rango seleccionado.")



    # --- SECCIÓN COMPARATIVA: ON-TIME vs IN-FULL (Expander) ---
    with st.expander("📊 Detalle de Pedidos (On-Time / In-Full)", expanded=False):
        st.markdown("---")
        col_ontime, col_infull = st.columns(2)

        # Lógica On-Time (Columna 1)
        with col_ontime:
            st.subheader("🚚 On-Time")
            total_ot = len(df_filt_ot)
            cumplen_ot = (df_filt_ot['Indicador'] == 'CUMPLE').sum()
            pct_ontime = (cumplen_ot / total_ot * 100) if total_ot > 0 else 0
            st.metric(label="⏱️ Cumplimiento", value=f"{pct_ontime:.1f}%", delta=f"{cumplen_ot} de {total_ot} pedidos")

            st.write("📋 **Lista de Pedidos On-Time**")
            st.dataframe(
                df_filt_ot[['numpedido', 'fechapedido', 'fechaentrega', 'Indicador']]
                .style.applymap(highlight_no_cumple, subset=['Indicador']),
                use_container_width=True,
                hide_index=True
            )

        # Lógica In-Full (Columna 2)
        with col_infull:
            st.subheader("📦 In-Full")
            total_pedidos = len(df_filt)
            pedidos_cumplen = (df_filt['Indicador'] == 'CUMPLE').sum()
            pct_infull = (pedidos_cumplen / total_pedidos * 100) if total_pedidos > 0 else 0
            st.metric(label="📈 Cumplimiento", value=f"{pct_infull:.1f}%", delta=f"{pedidos_cumplen} de {total_pedidos} pedidos")

            st.write("📋 **Lista de Pedidos In-Full**")
            st.dataframe(
                df_filt[['numpedido', 'fechapedido', 'cantpedida', 'cantentregada', 'Indicador']]
                .style.applymap(highlight_no_cumple, subset=['Indicador']),
                use_container_width=True,
                hide_index=True
            )



else:
    st.warning("Por favor seleccione un rango de fechas válido (Inicio y Fin).")
