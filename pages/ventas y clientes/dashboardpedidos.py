import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import sys, os

# Agregar la raíz del proyecto al path para importar funciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

conn = st.connection("sqlserver", type="sql")

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

st.markdown("# 📦 Dashboard de Pedidos")
st.write("Análisis y seguimiento de los pedidos de clientes.")

# -----------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------
df_pedidos = conn.query("""
SELECT [DocEntry]
      ,[NumPedido]
      ,[DocStatus]
      ,[DocType]
      ,[DocDate]
      ,[DocDueDate]
      ,[CardCode]
      ,[CardName]
      ,[SlpCode]
      ,[SlpName]
      ,[LineStatus]
      ,[ItemCode]
      ,[ItemName]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[TrnspName]
  FROM [SBO_HELA].[dbo].[Z_VIEW_PEDIDOS_HISTORICO]
""")

# -----------------------------------------------
# PRE-PROCESAMIENTO
# -----------------------------------------------
df_pedidos['DocDate_DT'] = pd.to_datetime(df_pedidos['DocDate'], errors='coerce')
df_pedidos['DocDueDate_DT'] = pd.to_datetime(df_pedidos['DocDueDate'], errors='coerce')
df_pedidos['Año'] = df_pedidos['DocDate_DT'].dt.year
df_pedidos['Mes'] = df_pedidos['DocDate_DT'].dt.month
df_pedidos['LineTotal_Num'] = pd.to_numeric(df_pedidos['LineTotal'], errors='coerce').fillna(0)
df_pedidos['Quantity_Num'] = pd.to_numeric(df_pedidos['Quantity'], errors='coerce').fillna(0)

_hoy = pd.Timestamp.today()
_año_hoy = _hoy.year
_año_ant = _año_hoy - 1

def fmt_m(val):
    if abs(val) >= 1_000_000:
        return f"M${val/1_000_000:,.1f}"
    elif abs(val) >= 1_000:
        return f"${val/1_000:,.0f}K"
    return f"${val:,.0f}"

# -----------------------------------------------
# MÉTRICAS PRINCIPALES DE PEDIDOS
# -----------------------------------------------
st.markdown("### 📊 Indicadores de Pedidos")

# Documentos únicos para métricas a nivel de pedido
df_pedidos_doc = df_pedidos.drop_duplicates('DocEntry')

# --- Pedidos año actual vs anterior ---
_pedidos_actual = df_pedidos_doc.loc[df_pedidos_doc['Año'] == _año_hoy, 'NumPedido'].nunique()
_pedidos_anterior = df_pedidos_doc.loc[df_pedidos_doc['Año'] == _año_ant, 'NumPedido'].nunique()
_delta_pedidos = _pedidos_actual - _pedidos_anterior

# --- Monto total pedidos año actual ---
_monto_actual = df_pedidos.loc[df_pedidos['Año'] == _año_hoy, 'LineTotal_Num'].sum()
_monto_anterior = df_pedidos.loc[df_pedidos['Año'] == _año_ant, 'LineTotal_Num'].sum()
_pct_monto = ((_monto_actual - _monto_anterior) / _monto_anterior * 100) if _monto_anterior != 0 else 0

# --- Pedidos abiertos ---
_pedidos_abiertos = df_pedidos_doc[df_pedidos_doc['DocStatus'] == 'O']['NumPedido'].nunique()

# --- Clientes con pedidos (año actual) ---
_clientes_pedidos = df_pedidos_doc.loc[df_pedidos_doc['Año'] == _año_hoy, 'CardCode'].nunique()

col_p1, col_p2, col_p3, col_p4 = st.columns(4)
col_p1.metric(
    f"📦 Pedidos {_año_hoy}",
    f"{_pedidos_actual}",
    delta=f"{_delta_pedidos:+d} vs {_año_ant}",
)
col_p2.metric(
    f"💰 Monto Pedidos {_año_hoy}",
    fmt_m(_monto_actual),
    delta=f"{_pct_monto:+.1f}% vs {_año_ant}",
)
col_p3.metric(
    "📂 Pedidos Abiertos",
    f"{_pedidos_abiertos}",
)
col_p4.metric(
    f"👥 Clientes c/Pedidos {_año_hoy}",
    f"{_clientes_pedidos}",
)

# -----------------------------------------------
# EVOLUCIÓN MENSUAL DE PEDIDOS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 📈 Evolución Mensual de Pedidos")

# Agrupar pedidos únicos por periodo mensual
df_evol_pedidos = (
    df_pedidos[df_pedidos['Año'].isin([_año_ant, _año_hoy])]
    .assign(periodo=lambda d: d['DocDate_DT'].dt.to_period('M'))
    .groupby('periodo')
    .agg(
        Cantidad=('NumPedido', 'nunique'),
        Monto=('LineTotal_Num', 'sum'),
    )
    .reset_index()
)
df_evol_pedidos['periodo_str'] = df_evol_pedidos['periodo'].astype(str)

if not df_evol_pedidos.empty:
    fig_evol = go.Figure()

    # Barras de monto
    fig_evol.add_trace(go.Bar(
        x=df_evol_pedidos['periodo_str'],
        y=df_evol_pedidos['Monto'],
        name='Monto Total',
        marker=dict(color='rgba(59,130,246,0.6)', line=dict(width=0)),
        hovertemplate='<b>%{x}</b><br>Monto: $%{y:,.0f}<extra></extra>',
        yaxis='y',
    ))

    # Línea de cantidad
    fig_evol.add_trace(go.Scatter(
        x=df_evol_pedidos['periodo_str'],
        y=df_evol_pedidos['Cantidad'],
        name='N° Pedidos',
        mode='lines+markers',
        line=dict(color='#f59e0b', width=2.5),
        marker=dict(size=7, color='#f59e0b'),
        hovertemplate='<b>%{x}</b><br>Pedidos: %{y}<extra></extra>',
        yaxis='y2',
    ))

    fig_evol.update_layout(
        xaxis=dict(title='Periodo', tickangle=-45),
        yaxis=dict(title='Monto ($)', showgrid=True, gridcolor='rgba(128,128,128,0.15)'),
        yaxis2=dict(
            title='N° Pedidos',
            overlaying='y',
            side='right',
            showgrid=False,
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=400,
        margin=dict(l=20, r=20, t=30, b=60),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.3,
    )
    st.plotly_chart(fig_evol, use_container_width=True)
else:
    st.info("Sin datos de evolución para mostrar.")

# -----------------------------------------------
# RANKING DE PEDIDOS POR VENDEDOR
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🏆 Ranking de Pedidos por Vendedor")

col_fi, col_ff = st.columns(2)
_fecha_min_ped = pd.Timestamp(f'{_año_hoy}-01-01').date()
_fecha_max_ped = _hoy.date()

with col_fi:
    _rango_ini_ped = st.date_input(
        "📅 Desde",
        value=_fecha_min_ped,
        min_value=df_pedidos['DocDate_DT'].min().date() if not df_pedidos.empty else _fecha_min_ped,
        max_value=_fecha_max_ped,
        key="ped_ranking_desde",
    )
with col_ff:
    _rango_fin_ped = st.date_input(
        "📅 Hasta",
        value=_fecha_max_ped,
        min_value=df_pedidos['DocDate_DT'].min().date() if not df_pedidos.empty else _fecha_min_ped,
        max_value=_fecha_max_ped,
        key="ped_ranking_hasta",
    )

_mask_ped_rango_full = (
    (df_pedidos['DocDate_DT'].dt.date >= _rango_ini_ped)
    & (df_pedidos['DocDate_DT'].dt.date <= _rango_fin_ped)
)
df_ranking_ped = (
    df_pedidos.loc[_mask_ped_rango_full]
    .groupby('SlpName', as_index=False)
    .agg(
        Pedidos=('NumPedido', 'nunique'),
        MontoTotal=('LineTotal_Num', 'sum'),
    )
    .sort_values('MontoTotal', ascending=True)
)

if not df_ranking_ped.empty:
    _max_monto_ped = df_ranking_ped['MontoTotal'].max()
    _colores_ped = [
        f'rgba(245,158,11,{0.35 + 0.65 * (v / _max_monto_ped)})' for v in df_ranking_ped['MontoTotal']
    ]

    fig_rank_ped = go.Figure(
        go.Bar(
            x=df_ranking_ped['MontoTotal'],
            y=df_ranking_ped['SlpName'],
            orientation='h',
            marker=dict(color=_colores_ped, line=dict(width=0)),
            text=df_ranking_ped['MontoTotal'].apply(fmt_m),
            textposition='outside',
            textfont=dict(size=12, color='#e2e8f0'),
            hovertemplate='<b>%{y}</b><br>Monto: %{x:$,.0f}<extra></extra>',
        )
    )
    fig_rank_ped.update_layout(
        title=dict(
            text=f'Pedidos acumulados por vendedor  ·  {_rango_ini_ped.strftime("%d/%m/%Y")} – {_rango_fin_ped.strftime("%d/%m/%Y")}',
            font=dict(size=15),
        ),
        xaxis=dict(title='Monto Total', showgrid=True, gridcolor='rgba(128,128,128,0.15)', zeroline=False),
        yaxis=dict(title='', tickfont=dict(size=12)),
        height=max(380, len(df_ranking_ped) * 38 + 80),
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.25,
    )
    st.plotly_chart(fig_rank_ped, use_container_width=True)
else:
    st.info("No hay datos de pedidos por vendedor para el rango seleccionado.")

# -----------------------------------------------
# TOP 10 CLIENTES POR PEDIDOS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🏅 Top 10 Clientes por Monto de Pedidos")

df_top_cli_ped = (
    df_pedidos.loc[_mask_ped_rango_full]
    .groupby('CardName', as_index=False)
    .agg(
        Pedidos=('NumPedido', 'nunique'),
        MontoTotal=('LineTotal_Num', 'sum'),
    )
    .sort_values('MontoTotal', ascending=False)
    .head(10)
    .sort_values('MontoTotal', ascending=True)
)

if not df_top_cli_ped.empty:
    _max_cli_ped = df_top_cli_ped['MontoTotal'].max()
    _colores_cp = [
        f'rgba(139,92,246,{0.35 + 0.65 * (v / _max_cli_ped)})' for v in df_top_cli_ped['MontoTotal']
    ]

    fig_top_cli = go.Figure(
        go.Bar(
            x=df_top_cli_ped['MontoTotal'],
            y=df_top_cli_ped['CardName'],
            orientation='h',
            marker=dict(color=_colores_cp, line=dict(width=0)),
            text=df_top_cli_ped['MontoTotal'].apply(fmt_m),
            textposition='outside',
            textfont=dict(size=12, color='#e2e8f0'),
            hovertemplate='<b>%{y}</b><br>Monto: %{x:$,.0f}<br>Pedidos: %{customdata}<extra></extra>',
            customdata=df_top_cli_ped['Pedidos'],
        )
    )
    fig_top_cli.update_layout(
        title=dict(text='Top 10 Clientes por Monto de Pedidos', font=dict(size=15)),
        xaxis=dict(title='Monto Total', showgrid=True, gridcolor='rgba(128,128,128,0.15)', zeroline=False),
        yaxis=dict(title='', tickfont=dict(size=11)),
        height=max(400, len(df_top_cli_ped) * 40 + 80),
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.25,
    )
    st.plotly_chart(fig_top_cli, use_container_width=True)
else:
    st.info("No hay datos de clientes con pedidos para el rango seleccionado.")

# -----------------------------------------------
# PEDIDOS POR ESTADO (PIE)
# -----------------------------------------------
st.markdown("---")
st.markdown("### 📊 Distribución de Pedidos por Estado")

col_pie1, col_pie2 = st.columns(2)

# Distribución por cantidad
df_estado_count = (
    df_pedidos_doc[df_pedidos_doc['Año'] == _año_hoy]
    .groupby('DocStatus')['NumPedido']
    .nunique()
    .reset_index()
    .rename(columns={'NumPedido': 'Cantidad'})
)
df_estado_count['Estado'] = df_estado_count['DocStatus'].map({'O': 'Abierto', 'C': 'Cerrado'}).fillna('Otro')

with col_pie1:
    if not df_estado_count.empty:
        fig_pie_q = go.Figure(go.Pie(
            labels=df_estado_count['Estado'],
            values=df_estado_count['Cantidad'],
            marker=dict(colors=['#3b82f6', '#22c55e', '#94a3b8']),
            hole=0.45,
            textinfo='label+percent+value',
            hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>%{percent}<extra></extra>',
        ))
        fig_pie_q.update_layout(
            title=dict(text='Por Cantidad', font=dict(size=14)),
            height=320,
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
        )
        st.plotly_chart(fig_pie_q, use_container_width=True)

# Distribución por monto
df_estado_monto = (
    df_pedidos[df_pedidos['Año'] == _año_hoy]
    .groupby('DocStatus')['LineTotal_Num']
    .sum()
    .reset_index()
    .rename(columns={'LineTotal_Num': 'Monto'})
)
df_estado_monto['Estado'] = df_estado_monto['DocStatus'].map({'O': 'Abierto', 'C': 'Cerrado'}).fillna('Otro')

with col_pie2:
    if not df_estado_monto.empty:
        fig_pie_m = go.Figure(go.Pie(
            labels=df_estado_monto['Estado'],
            values=df_estado_monto['Monto'],
            marker=dict(colors=['#3b82f6', '#22c55e', '#94a3b8']),
            hole=0.45,
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Monto: $%{value:,.0f}<br>%{percent}<extra></extra>',
        ))
        fig_pie_m.update_layout(
            title=dict(text='Por Monto', font=dict(size=14)),
            height=320,
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
        )
        st.plotly_chart(fig_pie_m, use_container_width=True)

# -----------------------------------------------
# DETALLE DE PEDIDOS CON FILTROS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Explorar Pedidos")

# Filtro de año
current_year_det = datetime.now().year
years_opts_det = sorted(df_pedidos['Año'].dropna().unique().astype(int).tolist())
years_rng_det = list(range(2022, current_year_det + 1))
default_yrs_det = [y for y in years_rng_det if y in years_opts_det]

selected_years_det = st.multiselect(
    "Filtrar por Año:",
    options=years_opts_det,
    default=[current_year_det] if current_year_det in years_opts_det else default_yrs_det[-1:],
    key="ped_detalle_años",
)

df_ped_detalle = df_pedidos[df_pedidos['Año'].isin(selected_years_det)].copy() if selected_years_det else df_pedidos.copy()

with st.expander("🔍 Filtros de Búsqueda", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        fp_numpedido = st.text_input("N° Pedido", key="ped_numpedido")
        fp_itemcode = st.text_input("Código Artículo", key="ped_itemcode")
    with fc2:
        fp_cardcode = st.text_input("CardCode", key="ped_cardcode")
        fp_itemname = st.text_input("Nombre Artículo", key="ped_itemname")
    with fc3:
        fp_cardname = st.text_input("Nombre Cliente", key="ped_cardname")
        fp_slpname = st.text_input("Vendedor", key="ped_slpname")

    if fp_numpedido:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['NumPedido'].astype(str).str.contains(fp_numpedido, case=False, na=False)]
    if fp_cardcode:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['CardCode'].astype(str).str.contains(fp_cardcode, case=False, na=False)]
    if fp_cardname:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['CardName'].astype(str).str.contains(fp_cardname, case=False, na=False)]
    if fp_slpname:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['SlpName'].astype(str).str.contains(fp_slpname, case=False, na=False)]
    if fp_itemcode:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['ItemCode'].astype(str).str.contains(fp_itemcode, case=False, na=False)]
    if fp_itemname:
        df_ped_detalle = df_ped_detalle[df_ped_detalle['ItemName'].astype(str).str.contains(fp_itemname, case=False, na=False)]

# Columnas a mostrar (limpias)
_cols_excluir = ['DocDate_DT', 'DocDueDate_DT', 'Año', 'Mes', 'LineTotal_Num', 'Quantity_Num', 'DocEntry']
_cols_view = [c for c in df_ped_detalle.columns if c not in _cols_excluir]
st.dataframe(df_ped_detalle[_cols_view], use_container_width=True, hide_index=True)

# Métricas del detalle filtrado
_cnt_ped = df_ped_detalle['NumPedido'].nunique()
_cnt_cli = df_ped_detalle['CardCode'].nunique()
_cnt_vnd = df_ped_detalle['SlpName'].nunique()
_tot_total = df_ped_detalle['LineTotal_Num'].sum()

cols_det = st.columns(4)
cols_det[0].metric("Pedidos", f"{_cnt_ped}")
cols_det[1].metric("Clientes", f"{_cnt_cli}")
cols_det[2].metric("Vendedores", f"{_cnt_vnd}")
cols_det[3].metric("Total Pedidos", f"${_tot_total:,.0f}")
