import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys, os

# Agregar la raíz del proyecto al path para importar funciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

conn = st.connection("sqlserver", type="sql")

st.markdown("# 🧑‍💼 Dashboard de Vendedores")
st.write("Análisis de desempeño, participación y evolución de ventas por vendedor.")

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

# Consolidado mensual de ventas netas por vendedor (FAV suma, NCV resta)
df_ventas_vendedores_mes = conn.query("""SELECT [slpname]
      ,[añomes]
      ,[neto]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_VENDEDORES_AÑO_MES]""")

# Detalle de ventas para análisis a nivel de vendedor
df_ventas = conn.query("""SELECT [CardCode]
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

# Presupuesto anual de vendedores
df_ppto = conn.query("""SELECT  [año]
      ,[slpcode]
      ,[slpname]
      ,[enero]
      ,[febrero]
      ,[marzo]
      ,[abril]
      ,[mayo]
      ,[junio]
      ,[julio]
      ,[agosto]
      ,[septiembre]
      ,[octubre]
      ,[noviembre]
      ,[diciembre]
      ,[enero_venta]
      ,[febrero_venta]
      ,[marzo_venta]
      ,[abril_venta]
      ,[mayo_venta]
      ,[junio_venta]
      ,[julio_venta]
      ,[agosto_venta]
      ,[septiembre_venta]
      ,[octubre_venta]
      ,[noviembre_venta]
      ,[diciembre_venta]
  FROM [SBO_HELA].[dbo].[Z_OSLP_PPTO]""")

# Detalle de pedidos para métricas cruzadas
df_pedidos = conn.query("""SELECT [DocEntry]
      ,[NumPedido]
      ,[DocStatus]
      ,[DocDate]
      ,[DocDueDate]
      ,[CardCode]
      ,[CardName]
      ,[SlpCode]
      ,[SlpName]
      ,[DocCur]
      ,[GrosProfit] as Neto
      ,[VatPaid] as IVA
      ,[DocTotal] as Total
      ,[LineStatus]
      ,[ItemCode]
      ,[ItemName]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[QtyKilos]
  FROM [SBO_HELA].[dbo].[Z_VIEW_PEDIDOS_CLIENTES_HISTORICO]""")

# -----------------------------------------------
# PRE-PROCESAMIENTO
# -----------------------------------------------
df_ventas['DocDate_DT'] = pd.to_datetime(df_ventas['DocDate'], errors='coerce')
df_ventas['Año'] = df_ventas['año']
df_ventas['Mes'] = df_ventas['mes']
df_ventas['LineTotal_Num'] = pd.to_numeric(df_ventas['LineTotal'], errors='coerce').fillna(0)
df_ventas['CostoTotal_Num'] = pd.to_numeric(df_ventas['CostoTotal'], errors='coerce').fillna(0)
df_ventas['Quantity_Num'] = pd.to_numeric(df_ventas['Quantity'], errors='coerce').fillna(0)

df_ventas_vendedores_mes['periodo_dt'] = pd.to_datetime(
    df_ventas_vendedores_mes['añomes'].astype(str), format='%Y%m', errors='coerce'
)
df_ventas_vendedores_mes['Año'] = df_ventas_vendedores_mes['periodo_dt'].dt.year
df_ventas_vendedores_mes['Mes'] = df_ventas_vendedores_mes['periodo_dt'].dt.month

df_pedidos['DocDate_DT'] = pd.to_datetime(df_pedidos['DocDate'], errors='coerce')
df_pedidos['Año'] = df_pedidos['DocDate_DT'].dt.year
df_pedidos['Total_Num'] = pd.to_numeric(df_pedidos['Total'], errors='coerce').fillna(0)

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
# MÉTRICAS PRINCIPALES DE VENDEDORES
# -----------------------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("### 📊 Indicadores de Vendedores")

# Documentos únicos a nivel de factura
df_ventas_doc = df_ventas.drop_duplicates('DocNum')

# Vendedores activos año actual vs anterior
_vendedores_activos_actual = df_ventas_doc.loc[
    df_ventas_doc['Año'] == _año_hoy, 'SlpName'
].nunique()

_vendedores_activos_anterior = df_ventas_doc.loc[
    df_ventas_doc['Año'] == _año_ant, 'SlpName'
].nunique()

_delta_vendedores = _vendedores_activos_actual - _vendedores_activos_anterior

# Ventas totales año actual por vendedores
_ventas_total_vendedores = df_ventas_vendedores_mes.loc[
    df_ventas_vendedores_mes['Año'] == _año_hoy, 'neto'
].sum()

_ventas_total_vendedores_ant = df_ventas_vendedores_mes.loc[
    df_ventas_vendedores_mes['Año'] == _año_ant, 'neto'
].sum()

_pct_var_ventas = ((_ventas_total_vendedores - _ventas_total_vendedores_ant) / _ventas_total_vendedores_ant * 100) if _ventas_total_vendedores_ant != 0 else 0

# Promedio de ventas por vendedor (año actual)
_promedio_vendedor = _ventas_total_vendedores / _vendedores_activos_actual if _vendedores_activos_actual > 0 else 0

# Top vendedor del año
df_top_vendedor = (
    df_ventas_vendedores_mes[df_ventas_vendedores_mes['Año'] == _año_hoy]
    .groupby('slpname', as_index=False)['neto'].sum()
    .sort_values('neto', ascending=False)
)
_top_vendedor_nombre = df_top_vendedor.iloc[0]['slpname'] if not df_top_vendedor.empty else "N/A"
_top_vendedor_monto = df_top_vendedor.iloc[0]['neto'] if not df_top_vendedor.empty else 0

col_v1, col_v2, col_v3, col_v4 = st.columns(4)
col_v1.metric(
    f"🧑‍💼 Vendedores Activos {_año_hoy}",
    f"{_vendedores_activos_actual}",
    delta=f"{_delta_vendedores:+d} vs {_año_ant}",
    height=150,
)
col_v2.metric(
    f"💰 Ventas Totales {_año_hoy}",
    fmt_m(_ventas_total_vendedores),
    delta=f"{_pct_var_ventas:+.1f}% vs {_año_ant}",
    height=150,
)
col_v3.metric(
    "📊 Promedio por Vendedor",
    fmt_m(_promedio_vendedor),
    delta=" ",
    height=150,
)
col_v4.metric(
    "🏆 Mejor Vendedor",
    _top_vendedor_nombre,
    delta=fmt_m(_top_vendedor_monto),
    delta_color="off",
    height=150,
)

# -----------------------------------------------
# RANKING DE VENTAS POR VENDEDOR
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🏆 Ranking de Ventas por Vendedor")

# Control de rango de fechas
col_fi, col_ff = st.columns(2)
_fecha_min_vnd = pd.Timestamp(f'{_año_hoy}-01-01').date()
_fecha_max_vnd = _hoy.date()

with col_fi:
    _rango_inicio_vnd = st.date_input(
        "📅 Desde",
        value=_fecha_min_vnd,
        min_value=df_ventas_vendedores_mes['periodo_dt'].min().date() if not df_ventas_vendedores_mes.empty else _fecha_min_vnd,
        max_value=_fecha_max_vnd,
        key="vnd_ranking_desde",
    )
with col_ff:
    _rango_fin_vnd = st.date_input(
        "📅 Hasta",
        value=_fecha_max_vnd,
        min_value=df_ventas_vendedores_mes['periodo_dt'].min().date() if not df_ventas_vendedores_mes.empty else _fecha_min_vnd,
        max_value=_fecha_max_vnd,
        key="vnd_ranking_hasta",
    )

# Filtrar y agrupar
_mask_vnd = (
    (df_ventas_vendedores_mes['periodo_dt'].dt.date >= _rango_inicio_vnd)
    & (df_ventas_vendedores_mes['periodo_dt'].dt.date <= _rango_fin_vnd)
)
df_ranking_vendedores = (
    df_ventas_vendedores_mes.loc[_mask_vnd]
    .groupby('slpname', as_index=False)['neto']
    .sum()
    .sort_values('neto', ascending=True)
)

if not df_ranking_vendedores.empty:
    _max_venta = df_ranking_vendedores['neto'].max()
    _colores = [
        f'rgba(59,130,246,{0.35 + 0.65 * (v / _max_venta)})' for v in df_ranking_vendedores['neto']
    ]

    fig_ranking = go.Figure(
        go.Bar(
            x=df_ranking_vendedores['neto'],
            y=df_ranking_vendedores['slpname'],
            orientation='h',
            marker=dict(color=_colores, line=dict(width=0)),
            text=df_ranking_vendedores['neto'].apply(fmt_m),
            textposition='outside',
            textfont=dict(size=12, color='#e2e8f0'),
            hovertemplate='<b>%{y}</b><br>Ventas: %{x:$,.0f}<extra></extra>',
        )
    )
    fig_ranking.update_layout(
        title=dict(
            text=f'Ventas acumuladas por vendedor  ·  {_rango_inicio_vnd.strftime("%d/%m/%Y")} – {_rango_fin_vnd.strftime("%d/%m/%Y")}',
            font=dict(size=15),
        ),
        xaxis=dict(title='Ventas Netas', showgrid=True, gridcolor='rgba(128,128,128,0.15)', zeroline=False),
        yaxis=dict(title='', tickfont=dict(size=12)),
        height=max(380, len(df_ranking_vendedores) * 38 + 80),
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.25,
    )
    st.plotly_chart(fig_ranking, use_container_width=True)
else:
    st.info("No hay datos de ventas por vendedor para el rango seleccionado.")

# -----------------------------------------------
# PARTICIPACIÓN DE MERCADO POR VENDEDOR (PIE)
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🥧 Participación de Ventas por Vendedor")

df_participacion = (
    df_ventas_vendedores_mes.loc[_mask_vnd]
    .groupby('slpname', as_index=False)['neto']
    .sum()
    .sort_values('neto', ascending=False)
)

if not df_participacion.empty:
    # Si hay muchos vendedores, agrupar los últimos en "Otros"
    if len(df_participacion) > 8:
        df_top_part = df_participacion.head(7).copy()
        _otros_total = df_participacion.iloc[7:]['neto'].sum()
        df_otros = pd.DataFrame({'slpname': ['Otros'], 'neto': [_otros_total]})
        df_participacion_chart = pd.concat([df_top_part, df_otros], ignore_index=True)
    else:
        df_participacion_chart = df_participacion.copy()

    _colores_pie = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#94a3b8']

    fig_pie = go.Figure(go.Pie(
        labels=df_participacion_chart['slpname'],
        values=df_participacion_chart['neto'],
        marker=dict(colors=_colores_pie[:len(df_participacion_chart)]),
        hole=0.45,
        textinfo='label+percent',
        textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>Ventas: $%{value:,.0f}<br>%{percent}<extra></extra>',
    ))
    fig_pie.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5),
    )
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Sin datos para mostrar la participación.")

# -----------------------------------------------
# EVOLUCIÓN MENSUAL DE VENTAS POR VENDEDOR
# -----------------------------------------------
st.markdown("---")
st.markdown("### 📈 Evolución Mensual de Ventas por Vendedor")

# Selector de vendedores para la evolución
_vendedores_disponibles = sorted(
    df_ventas_vendedores_mes.loc[
        df_ventas_vendedores_mes['Año'].isin([_año_ant, _año_hoy]), 'slpname'
    ].dropna().unique().tolist()
)

# Por defecto seleccionar los top 5 vendedores del año actual
_top5_default = (
    df_ventas_vendedores_mes[df_ventas_vendedores_mes['Año'] == _año_hoy]
    .groupby('slpname')['neto'].sum()
    .nlargest(5)
    .index.tolist()
)

_vendedores_seleccionados = st.multiselect(
    "Seleccione vendedores a comparar:",
    options=_vendedores_disponibles,
    default=_top5_default,
    key="vnd_evol_selector",
)

if _vendedores_seleccionados:
    df_evol_vnd = (
        df_ventas_vendedores_mes[
            (df_ventas_vendedores_mes['slpname'].isin(_vendedores_seleccionados))
            & (df_ventas_vendedores_mes['Año'].isin([_año_ant, _año_hoy]))
        ]
        .assign(periodo_str=lambda d: d['periodo_dt'].dt.strftime('%Y-%m'))
        .groupby(['periodo_str', 'slpname'], as_index=False)['neto']
        .sum()
        .sort_values('periodo_str')
    )

    if not df_evol_vnd.empty:
        _colores_lineas = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#f97316', '#14b8a6', '#a855f7']

        fig_evol = go.Figure()
        for i, vendedor in enumerate(_vendedores_seleccionados):
            df_v = df_evol_vnd[df_evol_vnd['slpname'] == vendedor]
            fig_evol.add_trace(go.Scatter(
                x=df_v['periodo_str'],
                y=df_v['neto'],
                mode='lines+markers',
                name=vendedor,
                line=dict(color=_colores_lineas[i % len(_colores_lineas)], width=2.5),
                marker=dict(size=6),
                hovertemplate=f'<b>{vendedor}</b><br>Periodo: %{{x}}<br>Ventas: $%{{y:,.0f}}<extra></extra>',
            ))

        fig_evol.update_layout(
            xaxis=dict(title='Periodo', tickangle=-45),
            yaxis=dict(title='Ventas Netas', showgrid=True, gridcolor='rgba(128,128,128,0.15)'),
            height=450,
            margin=dict(l=20, r=20, t=30, b=60),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            hovermode='x unified',
        )
        st.plotly_chart(fig_evol, use_container_width=True)
    else:
        st.info("Sin datos de evolución para los vendedores seleccionados.")
else:
    st.info("Seleccione al menos un vendedor para visualizar la evolución.")

# -----------------------------------------------
# COMPARATIVO AÑO ACTUAL VS ANTERIOR POR VENDEDOR
# -----------------------------------------------
st.markdown("---")
st.markdown(f"### 📊 Comparativo {_año_hoy} vs {_año_ant} por Vendedor")

_mes_limite = _hoy.month

df_comp_actual = (
    df_ventas_vendedores_mes[
        (df_ventas_vendedores_mes['Año'] == _año_hoy)
        & (df_ventas_vendedores_mes['Mes'] <= _mes_limite)
    ]
    .groupby('slpname', as_index=False)['neto'].sum()
    .rename(columns={'neto': f'Ventas {_año_hoy}'})
)

df_comp_anterior = (
    df_ventas_vendedores_mes[
        (df_ventas_vendedores_mes['Año'] == _año_ant)
        & (df_ventas_vendedores_mes['Mes'] <= _mes_limite)
    ]
    .groupby('slpname', as_index=False)['neto'].sum()
    .rename(columns={'neto': f'Ventas {_año_ant}'})
)

df_comparativo = pd.merge(df_comp_actual, df_comp_anterior, on='slpname', how='outer').fillna(0)
df_comparativo['Variación %'] = (
    (df_comparativo[f'Ventas {_año_hoy}'] - df_comparativo[f'Ventas {_año_ant}'])
    / df_comparativo[f'Ventas {_año_ant}'].replace(0, np.nan) * 100
).fillna(0).round(1)
df_comparativo = df_comparativo.sort_values(f'Ventas {_año_hoy}', ascending=True)

if not df_comparativo.empty:
    fig_comp = go.Figure()

    fig_comp.add_trace(go.Bar(
        x=df_comparativo[f'Ventas {_año_ant}'],
        y=df_comparativo['slpname'],
        name=str(_año_ant),
        orientation='h',
        marker=dict(color='rgba(148,163,184,0.6)', line=dict(width=0)),
        hovertemplate='<b>%{y}</b><br>' + str(_año_ant) + ': $%{x:,.0f}<extra></extra>',
    ))

    fig_comp.add_trace(go.Bar(
        x=df_comparativo[f'Ventas {_año_hoy}'],
        y=df_comparativo['slpname'],
        name=str(_año_hoy),
        orientation='h',
        marker=dict(color='rgba(59,130,246,0.8)', line=dict(width=0)),
        hovertemplate='<b>%{y}</b><br>' + str(_año_hoy) + ': $%{x:,.0f}<extra></extra>',
    ))

    fig_comp.update_layout(
        title=dict(
            text=f'Mismo periodo (Ene–{_hoy.strftime("%b")})',
            font=dict(size=14),
        ),
        barmode='group',
        xaxis=dict(title='Ventas Netas', showgrid=True, gridcolor='rgba(128,128,128,0.15)', zeroline=False),
        yaxis=dict(title='', tickfont=dict(size=12)),
        height=max(400, len(df_comparativo) * 45 + 80),
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.20,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.info("Sin datos comparativos disponibles.")

# -----------------------------------------------
# VENDEDORES POR CLIENTES Y KILOS
# -----------------------------------------------
st.markdown("---")
st.markdown(f"### 🧮 Indicadores por Vendedor – {_año_hoy}")

# Filtro por rango de fechas del ranking ya existente
_mask_fact_rango = (
    (df_ventas['DocDate_DT'].dt.date >= _rango_inicio_vnd)
    & (df_ventas['DocDate_DT'].dt.date <= _rango_fin_vnd)
)

df_vendedor_detalle = (
    df_ventas[_mask_fact_rango]
    .groupby('SlpName', as_index=False)
    .agg(
        Facturas=('DocNum', 'nunique'),
        Clientes=('CardCode', 'nunique'),
        neto=('LineTotal_Num', 'sum'),
        Items=('ItemCode', 'nunique'),
    )
    .sort_values('neto', ascending=False)
)
df_vendedor_detalle['neto'] = df_vendedor_detalle['neto'].round(0)
df_vendedor_detalle['Ticket Promedio'] = (
    df_vendedor_detalle['neto'] / df_vendedor_detalle['Facturas'].replace(0, np.nan)
).fillna(0).round(0)

st.dataframe(df_vendedor_detalle, use_container_width=True, hide_index=True)

# Métricas resumen
_total_fact_v = df_vendedor_detalle['Facturas'].sum()
_total_cli_v = df_vendedor_detalle['Clientes'].sum()
_total_vn_v = df_vendedor_detalle['neto'].sum()

cols_r = st.columns(3)
cols_r[0].metric("Facturas", f"{_total_fact_v:,.0f}")
cols_r[1].metric("Clientes Atendidos", f"{_total_cli_v:,.0f}")
cols_r[2].metric("Ventas Netas", fmt_m(_total_vn_v))

# -----------------------------------------------
# CLIENTES POR VENDEDOR (TREEMAP)
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🗺️ Distribución de Clientes por Vendedor")

df_cli_vendedor = (
    df_ventas[_mask_fact_rango]
    .groupby(['SlpName', 'CardName'], as_index=False)['LineTotal_Num']
    .sum()
    .rename(columns={'LineTotal_Num': 'neto'})
    .sort_values('neto', ascending=False)
)

if not df_cli_vendedor.empty:
    # Limitar a top clientes por vendedor para legibilidad
    df_treemap = df_cli_vendedor.copy()
    df_treemap = df_treemap[df_treemap['neto'] > 0]

    if not df_treemap.empty:
        fig_tree = px.treemap(
            df_treemap,
            path=['SlpName', 'CardName'],
            values='neto',
            color='neto',
            color_continuous_scale='Blues',
            hover_data={'neto': ':$,.0f'},
        )
        fig_tree.update_layout(
            height=500,
            margin=dict(l=10, r=10, t=30, b=10),
            coloraxis_showscale=False,
        )
        fig_tree.update_traces(
            hovertemplate='<b>%{label}</b><br>Ventas: $%{value:,.0f}<extra></extra>',
            textinfo='label+value',
            texttemplate='%{label}<br>$%{value:,.0f}',
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("Sin datos positivos de clientes por vendedor.")
else:
    st.info("Sin datos de distribución de clientes por vendedor.")

# -----------------------------------------------
# DETALLE DE FACTURACIÓN POR VENDEDOR CON FILTROS
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Explorar Facturación por Vendedor")

# Filtro de año
current_year_det = datetime.now().year
years_opts = sorted(df_ventas['Año'].dropna().unique().astype(int).tolist())
years_rng = list(range(2022, current_year_det + 1))
default_yrs = [y for y in years_rng if y in years_opts]

selected_years_det = st.multiselect(
    "Filtrar por Año:",
    options=years_opts,
    default=[current_year_det] if current_year_det in years_opts else default_yrs[-1:],
    key="vnd_detalle_años",
)

df_vnd_detalle = df_ventas[df_ventas['Año'].isin(selected_years_det)].copy() if selected_years_det else df_ventas.copy()

with st.expander("🔍 Filtros de Búsqueda", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        fv_slpname = st.text_input("Vendedor", key="vnd_slpname")
        fv_cardcode = st.text_input("CardCode", key="vnd_cardcode")
    with fc2:
        fv_cardname = st.text_input("Nombre Cliente", key="vnd_cardname")
        fv_itemname = st.text_input("Artículo", key="vnd_itemname")
    with fc3:
        fv_docnum = st.text_input("N° Factura", key="vnd_docnum")
        fv_itemcode = st.text_input("Código Artículo", key="vnd_itemcode")

    if fv_slpname:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['SlpName'].astype(str).str.contains(fv_slpname, case=False, na=False)]
    if fv_cardcode:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['CardCode'].astype(str).str.contains(fv_cardcode, case=False, na=False)]
    if fv_cardname:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['CardName'].astype(str).str.contains(fv_cardname, case=False, na=False)]
    if fv_itemname:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['ItemName'].astype(str).str.contains(fv_itemname, case=False, na=False)]
    if fv_docnum:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['DocNum'].astype(str).str.contains(fv_docnum, case=False, na=False)]
    if fv_itemcode:
        df_vnd_detalle = df_vnd_detalle[df_vnd_detalle['ItemCode'].astype(str).str.contains(fv_itemcode, case=False, na=False)]

# Columnas a mostrar (limpias)
_cols_excluir = ['DocDate_DT', 'Año', 'Mes', 'LineTotal_Num', 'CostoTotal_Num', 'Quantity_Num', 'año', 'mes']
_cols_view = [c for c in df_vnd_detalle.columns if c not in _cols_excluir]
st.dataframe(df_vnd_detalle[_cols_view], use_container_width=True, hide_index=True)

# Métricas del detalle filtrado
_cnt_fact = df_vnd_detalle['DocNum'].nunique()
_cnt_cli = df_vnd_detalle['CardCode'].nunique()
_cnt_vnd = df_vnd_detalle['SlpName'].nunique()
_tot_total = df_vnd_detalle['LineTotal_Num'].sum()

cols_det = st.columns(4)
cols_det[0].metric("Facturas", f"{_cnt_fact}")
cols_det[1].metric("Clientes", f"{_cnt_cli}")
cols_det[2].metric("Vendedores", f"{_cnt_vnd}")
cols_det[3].metric("Total Ventas", f"${_tot_total:,.0f}")

# ──────────────────────────────────────────────────────────────────────────────
# NUEVA SECCIÓN: PRESUPUESTO VS VENTAS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Cumplimiento de Presupuesto Anual")
st.write("Comparativa detallada entre el presupuesto asignado y las ventas reales por mes.")

if not df_ppto.empty:
    # Filtro de año específico para presupuesto
    col_y1, col_y2 = st.columns([2, 2])
    with col_y1:
        ppto_years = sorted(df_ppto['año'].unique().tolist(), reverse=True)
        selected_ppto_year = st.selectbox("📅 Año del Presupuesto:", options=ppto_years, index=0 if ppto_years else None)
    
    df_ppto_filt_year = df_ppto[df_ppto['año'] == selected_ppto_year].copy()
    
    # ─── NUEVOS FILTROS DE VENDEDORES ───
    st.markdown("#### ⚙️ Filtros de Visualización")
    cf1, cf2, cf3 = st.columns([2, 1, 1])
    
    with cf1:
        vendedores_ppto = sorted(df_ppto_filt_year['slpname'].unique().tolist())
        selected_vendedores = st.multiselect("👤 Seleccionar Vendedores:", options=vendedores_ppto, default=[])
    
    with cf2:
        # Switch para mostrar solo los que tienen movimiento
        show_only_movement = st.toggle("Mostrar solo con movimiento", value=True, help="Muestra vendedores con ventas > 0 en el año.")
    
    with cf3:
        # Switch para mostrar todos (desactiva el filtro de movimiento si se activa)
        show_all = st.toggle("Mostrar todos", value=False)

    # Lógica de filtrado
    df_ppto_filt = df_ppto_filt_year.copy()
    
    # Calcular movimiento total del año para cada fila
    meses_venta_cols = [f"{m}_venta" for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']]
    df_ppto_filt['movimiento_total'] = df_ppto_filt[meses_venta_cols].sum(axis=1)

    if not show_all:
        if show_only_movement:
            df_ppto_filt = df_ppto_filt[df_ppto_filt['movimiento_total'] > 0]
        
    if selected_vendedores:
        df_ppto_filt = df_ppto_filt[df_ppto_filt['slpname'].isin(selected_vendedores)]

    if df_ppto_filt.empty:
        st.warning(f"⚠️ No hay datos para los filtros seleccionados en el año {selected_ppto_year}")
        st.stop()

    # 1. Cuadro de Vendedores y Presupuesto
    # Seleccionamos las columnas en el orden solicitado
    meses_nombres = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    cols_display = ['slpname']
    for mes in meses_nombres:
        cols_display.append(mes)
        cols_display.append(f"{mes}_venta")
    
    # Formatear el dataframe para mostrar en el grid
    df_ppto_view = df_ppto_filt[cols_display].copy()
    
    # Renombrar columnas para que se vean mejor
    renames = {'slpname': 'Vendedor'}
    for mes in meses_nombres:
        renames[mes] = f"{mes.capitalize()} PPTO"
        renames[f"{mes}_venta"] = f"{mes.capitalize()} Venta"
    
    df_ppto_view = df_ppto_view.rename(columns=renames)
    
    st.dataframe(df_ppto_view, use_container_width=True, hide_index=True)
    
    # 2. Gráfico de Delta %
    st.markdown("#### 📈 Desviación Porcentual por Mes")
    
    # Meltear los datos para graficar con Plotly
    deltas = []
    for index, row in df_ppto_filt.iterrows():
        vendedor = row['slpname']
        año_ppto = row['año']
        for mes in meses_nombres:
            ppto = float(row[mes])
            venta = float(row[f"{mes}_venta"])
            # Delta % = ((Venta / PPTO) - 1) * 100
            delta_pct = ((venta / ppto) - 1) * 100 if ppto > 0 else 0
            deltas.append({
                'Vendedor': f"{vendedor} ({año_ppto})",
                'Mes': mes.capitalize(),
                'Delta %': delta_pct,
                'PPTO': ppto,
                'Venta': venta
            })
    
    df_deltas = pd.DataFrame(deltas)
    
    if not df_deltas.empty:
        fig_delta = px.line(
            df_deltas, 
            x='Mes', 
            y='Delta %', 
            color='Vendedor',
            markers=True,
            title="Cumplimiento de Meta (%)",
            hover_data={'Mes': True, 'Delta %': ':.2f', 'PPTO': ':$,.0f', 'Venta': ':$,.0f'}
        )
        
        fig_delta.update_layout(
            yaxis_title="Variación % (Venta vs PPTO)",
            xaxis_title="Meses",
            height=500,
            hovermode="x unified"
        )
        
        # Línea de referencia en 0% (Cumplimiento exacto)
        fig_delta.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Meta 0%")
        
        st.plotly_chart(fig_delta, use_container_width=True)
else:
    st.info("ℹ️ No se encontraron datos de presupuesto en la base de datos.")
