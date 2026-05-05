import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os

# Agregar la raíz del proyecto al path para importar funciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

conn = st.connection("sqlserver", type="sql")

st.markdown("# 👥 Dashboard de Clientes")
st.write("Análisis de la cartera de clientes, evolución y concentración de ventas.")

# --- CSS personalizado para métricas tipo tarjeta premium ---
st.markdown("""
<style>
/* ==========================================
   METRIC CARDS – Estilo premium con soporte
   para tema claro y oscuro de Streamlit
   ========================================== */

/* Contenedor de cada métrica */
[data-testid="stMetric"] {
    background: var(--metric-bg, #ffffff);
    border: 1px solid var(--metric-border, #e8ecf1);
    border-radius: 14px;
    padding: 20px 24px 16px 24px;
    box-shadow: 0 2px 8px var(--metric-shadow, rgba(0,0,0,0.06));
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 16px var(--metric-shadow-hover, rgba(0,0,0,0.10));
    transform: translateY(-2px);
}

/* Label (título de la métrica) */
[data-testid="stMetric"] label[data-testid="stMetricLabel"] {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    text-transform: none;
    color: var(--metric-label, #6b7b8d) !important;
}

/* Valor principal */
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: var(--metric-value, #1a2332) !important;
    line-height: 1.2;
    padding-top: 6px;
}

/* Delta (variación) */
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding-top: 2px;
}

/* ======= TEMA CLARO (por defecto) ======= */
:root {
    --metric-bg: #ffffff;
    --metric-border: #e8ecf1;
    --metric-shadow: rgba(0,0,0,0.05);
    --metric-shadow-hover: rgba(0,0,0,0.10);
    --metric-label: #6b7b8d;
    --metric-value: #1a2332;
}

/* ======= TEMA OSCURO ======= */
@media (prefers-color-scheme: dark) {
    :root {
        --metric-bg: #1e2530;
        --metric-border: #2d3748;
        --metric-shadow: rgba(0,0,0,0.25);
        --metric-shadow-hover: rgba(0,0,0,0.40);
        --metric-label: #94a3b8;
        --metric-value: #e2e8f0;
    }
}
/* Streamlit dark mode override (class-based) */
[data-testid="stAppViewContainer"][class*="dark"],
.stApp[data-theme="dark"] {
    --metric-bg: #1e2530;
    --metric-border: #2d3748;
    --metric-shadow: rgba(0,0,0,0.25);
    --metric-shadow-hover: rgba(0,0,0,0.40);
    --metric-label: #94a3b8;
    --metric-value: #e2e8f0;
}

/* Ajuste de gap entre columnas de métricas */
[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------

# Ventas por cliente agrupadas por mes
df_ventas_mes = conn.query("""SELECT [AñoMes]
      ,[CardName]
      ,[VentasNetas]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_CLIENTES_AÑO_MES]""")

# Detalle de ventas para análisis a nivel de cliente
df_facturas = conn.query("""SELECT  [CardCode]
      ,[CardName]
      ,[Notes]
      ,[SlpName]
      ,[DocNum]
      ,[año]
      ,[mes]
      ,[DocDate]
      ,[ItemCode]
      ,[Dscription]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[CostoTotal]
      ,[Margen]
      ,[UnitMsr]
      ,[stockprice]
  FROM [SBO_HELA].[dbo].[Z_VIEW_VENTAS_HISTORICO]""")

# -----------------------------------------------
# PRE-PROCESAMIENTO
# -----------------------------------------------
df_facturas['DocDate_DT'] = pd.to_datetime(df_facturas['DocDate'], errors='coerce')
df_facturas['Año'] = df_facturas['año']
df_facturas['Mes'] = df_facturas['mes']
df_facturas['LineTotal_Num'] = pd.to_numeric(df_facturas['LineTotal'], errors='coerce').fillna(0)
df_facturas['Quantity_Num'] = pd.to_numeric(df_facturas['Quantity'], errors='coerce').fillna(0)

df_ventas_mes['periodo_dt'] = pd.to_datetime(
    df_ventas_mes['AñoMes'].astype(str), format='%Y%m', errors='coerce'
)
df_ventas_mes['Año'] = df_ventas_mes['periodo_dt'].dt.year
df_ventas_mes['Mes'] = df_ventas_mes['periodo_dt'].dt.month

_hoy = pd.Timestamp.today()
_año_hoy = _hoy.year
_año_ant = _año_hoy - 1

# -----------------------------------------------
# MÉTRICAS PRINCIPALES DE CLIENTES
# -----------------------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("### 📊 Indicadores de Clientes")

# Documentos únicos para métricas a nivel de documento
df_facturas_doc = df_facturas.drop_duplicates('DocNum')

# Clientes activos año actual (con al menos 1 factura)
_clientes_activos_actual = df_facturas_doc.loc[
    df_facturas_doc['DocDate_DT'].dt.year == _año_hoy, 'CardCode'
].nunique()

_clientes_activos_anterior = df_facturas_doc.loc[
    df_facturas_doc['DocDate_DT'].dt.year == _año_ant, 'CardCode'
].nunique()

_delta_clientes = _clientes_activos_actual - _clientes_activos_anterior

# Clientes nuevos (facturaron en el año actual pero NO en años anteriores)
_clientes_historicos = set(
    df_facturas_doc.loc[df_facturas_doc['DocDate_DT'].dt.year < _año_hoy, 'CardCode'].unique()
)
_clientes_año_actual = set(
    df_facturas_doc.loc[df_facturas_doc['DocDate_DT'].dt.year == _año_hoy, 'CardCode'].unique()
)
_clientes_nuevos = len(_clientes_año_actual - _clientes_historicos)

# Ticket promedio por cliente (año actual)
_total_ventas_actual = df_facturas.loc[df_facturas['Año'] == _año_hoy, 'LineTotal_Num'].sum()
_ticket_promedio = _total_ventas_actual / _clientes_activos_actual if _clientes_activos_actual > 0 else 0

# Concentración: % ventas top 5 clientes
df_clientes_actual = (
    df_ventas_mes[df_ventas_mes['Año'] == _año_hoy]
    .groupby('CardName', as_index=False)['VentasNetas'].sum()
    .sort_values('VentasNetas', ascending=False)
)
_total_ventas_netas = df_clientes_actual['VentasNetas'].sum()
_top5_ventas = df_clientes_actual.head(5)['VentasNetas'].sum()
_pct_top5 = (_top5_ventas / _total_ventas_netas * 100) if _total_ventas_netas > 0 else 0

def fmt_m(val):
    if abs(val) >= 1_000_000:
        return f"M${val/1_000_000:,.1f}"
    elif abs(val) >= 1_000:
        return f"${val/1_000:,.0f}K"
    return f"${val:,.0f}"

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric(
    f"👥 Clientes Activos {_año_hoy}",
    f"{_clientes_activos_actual}",
    delta=f"{_delta_clientes:+d} vs {_año_ant}",
    height=150,
)
col_m2.metric(
    f"🆕 Clientes Nuevos {_año_hoy}",
    f"{_clientes_nuevos}",
    delta=" ",
    height=150,
)
col_m3.metric(
    "💳 Ticket Promedio",
    fmt_m(_ticket_promedio),
    delta=" ",
    height=150,
)
col_m4.metric(
    "🎯 Concentración Top 5",
    f"{_pct_top5:.1f}%",
    delta="del total de ventas",
    height=150,
)

# -----------------------------------------------
# RANKING TOP 10 CLIENTES (AÑO ACTUAL)
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🏆 Top 10 Clientes por Ventas")

# Control de rango de fechas para el ranking
col_fi, col_ff = st.columns(2)
_fecha_min_cli = pd.Timestamp(f'{_año_hoy}-01-01').date()
_fecha_max_cli = _hoy.date()

with col_fi:
    _rango_inicio_cli = st.date_input(
        "📅 Desde",
        value=_fecha_min_cli,
        min_value=df_ventas_mes['periodo_dt'].min().date() if not df_ventas_mes.empty else _fecha_min_cli,
        max_value=_fecha_max_cli,
        key="cli_ranking_desde",
    )
with col_ff:
    _rango_fin_cli = st.date_input(
        "📅 Hasta",
        value=_fecha_max_cli,
        min_value=df_ventas_mes['periodo_dt'].min().date() if not df_ventas_mes.empty else _fecha_min_cli,
        max_value=_fecha_max_cli,
        key="cli_ranking_hasta",
    )

# Filtrar y agrupar
_mask_cli = (
    (df_ventas_mes['periodo_dt'].dt.date >= _rango_inicio_cli)
    & (df_ventas_mes['periodo_dt'].dt.date <= _rango_fin_cli)
)
df_top_clientes = (
    df_ventas_mes.loc[_mask_cli]
    .groupby('CardName', as_index=False)['VentasNetas']
    .sum()
    .sort_values('VentasNetas', ascending=False)
    .head(10)
    .sort_values('VentasNetas', ascending=True)
)

if not df_top_clientes.empty:
    _max_v = df_top_clientes['VentasNetas'].max()
    _colores_cli = [
        f'rgba(34,197,94,{0.35 + 0.65 * (v / _max_v)})' for v in df_top_clientes['VentasNetas']
    ]

    fig_top = go.Figure(
        go.Bar(
            x=df_top_clientes['VentasNetas'],
            y=df_top_clientes['CardName'],
            orientation='h',
            marker=dict(color=_colores_cli, line=dict(width=0)),
            text=df_top_clientes['VentasNetas'].apply(fmt_m),
            textposition='outside',
            textfont=dict(size=12, color='#e2e8f0'),
            hovertemplate='<b>%{y}</b><br>Ventas: %{x:$,.0f}<extra></extra>',
        )
    )
    fig_top.update_layout(
        title=dict(
            text=f'Top 10 Clientes  ·  {_rango_inicio_cli.strftime("%d/%m/%Y")} – {_rango_fin_cli.strftime("%d/%m/%Y")}',
            font=dict(size=15),
        ),
        xaxis=dict(title='Ventas Netas', showgrid=True, gridcolor='rgba(128,128,128,0.15)', zeroline=False),
        yaxis=dict(title='', tickfont=dict(size=11)),
        height=max(400, len(df_top_clientes) * 40 + 80),
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.25,
    )
    st.plotly_chart(fig_top, use_container_width=True)
else:
    st.info("No hay datos de clientes para el rango seleccionado.")

# -----------------------------------------------
# EVOLUCIÓN MENSUAL DE CLIENTES ACTIVOS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 📈 Evolución Mensual de Clientes Activos")

# Clientes únicos por mes (basado en facturación)
df_cli_evol = (
    df_facturas_doc[df_facturas_doc['DocDate_DT'].dt.year.isin([_año_ant, _año_hoy])]
    .assign(periodo=lambda d: d['DocDate_DT'].dt.to_period('M'))
    .groupby('periodo')['CardCode']
    .nunique()
    .reset_index()
    .rename(columns={'CardCode': 'Clientes'})
)
df_cli_evol['periodo_str'] = df_cli_evol['periodo'].astype(str)

if not df_cli_evol.empty:
    fig_evol = go.Figure(
        go.Scatter(
            x=df_cli_evol['periodo_str'],
            y=df_cli_evol['Clientes'],
            mode='lines+markers',
            line=dict(color='#8b5cf6', width=2.5),
            marker=dict(size=7, color='#8b5cf6'),
            fill='tozeroy',
            fillcolor='rgba(139,92,246,0.10)',
            hovertemplate='<b>%{x}</b><br>Clientes: %{y}<extra></extra>',
        )
    )
    fig_evol.update_layout(
        xaxis=dict(title='Periodo', tickangle=-45),
        yaxis=dict(title='N° Clientes Únicos', showgrid=True, gridcolor='rgba(128,128,128,0.15)'),
        height=360,
        margin=dict(l=20, r=20, t=30, b=60),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig_evol, use_container_width=True)
else:
    st.info("Sin datos de evolución para mostrar.")

# -----------------------------------------------
# DETALLE DE CLIENTES CON FILTROS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Detalle de Ventas por Cliente")

# Año selector
current_year = datetime.now().year
years_options = sorted(df_facturas['Año'].dropna().unique().astype(int).tolist())
years_range = list(range(2022, current_year + 1))
default_years = [y for y in years_range if y in years_options]

selected_years = st.multiselect(
    "Filtrar por Año:",
    options=years_options,
    default=[current_year] if current_year in years_options else default_years[-1:],
    key="cli_detalle_años",
)

df_cli_detalle = df_facturas[df_facturas['Año'].isin(selected_years)].copy() if selected_years else df_facturas.copy()

with st.expander("🔍 Filtros de Búsqueda", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_cardcode = st.text_input("CardCode", key="cli_cardcode")
        f_slpname = st.text_input("Vendedor", key="cli_slpname")
    with fc2:
        f_cardname = st.text_input("Nombre Cliente", key="cli_cardname")
        f_itemname = st.text_input("Artículo", key="cli_itemname")
    with fc3:
        f_trnspname = st.text_input("Transportista", key="cli_trnspname")

    if f_cardcode:
        df_cli_detalle = df_cli_detalle[df_cli_detalle['CardCode'].astype(str).str.contains(f_cardcode, case=False, na=False)]
    if f_cardname:
        df_cli_detalle = df_cli_detalle[df_cli_detalle['CardName'].astype(str).str.contains(f_cardname, case=False, na=False)]
    if f_slpname:
        df_cli_detalle = df_cli_detalle[df_cli_detalle['SlpName'].astype(str).str.contains(f_slpname, case=False, na=False)]
    if f_itemname:
        df_cli_detalle = df_cli_detalle[df_cli_detalle['Dscription'].astype(str).str.contains(f_itemname, case=False, na=False)]
    if f_trnspname:
        df_cli_detalle = df_cli_detalle[df_cli_detalle['TrnspName'].astype(str).str.contains(f_trnspname, case=False, na=False)]

# Resumen agrupado por cliente
df_resumen_cli = (
    df_cli_detalle.groupby(['CardCode', 'CardName'], as_index=False)
    .agg(
        Facturas=('DocNum', 'nunique'),
        VentasNetas=('LineTotal_Num', 'sum'),
        Items=('ItemCode', 'nunique'),
    )
    .sort_values('VentasNetas', ascending=False)
)
df_resumen_cli['VentasNetas'] = df_resumen_cli['VentasNetas'].round(0)

st.dataframe(df_resumen_cli, use_container_width=True, hide_index=True)

# Métricas del resumen filtrado
_total_cli = df_resumen_cli['CardCode'].nunique()
_total_fact = df_resumen_cli['Facturas'].sum()
_total_vn = df_resumen_cli['VentasNetas'].sum()

cols_r = st.columns(3)
cols_r[0].metric("Clientes", f"{_total_cli}")
cols_r[1].metric("Facturas", f"{_total_fact:,.0f}")
cols_r[2].metric("Ventas Netas", fmt_m(_total_vn))
