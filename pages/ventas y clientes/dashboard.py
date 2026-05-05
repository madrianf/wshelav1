import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns   
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os

# Agregar la raíz del proyecto al path para importar funciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from funciones.calculaotif import calcular_otif

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
    font-size: 2.73rem !important;
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

st.markdown("# Panel de Control Ventas y Clientes")
st.write("Bienvenido al dashboard central de ventas.")

# -----------------------------------------------
# CARGA DE DATOS (DATA LAYER)
# -----------------------------------------------

# df_entregas: Detalle histórico de entregas (despachos) realizados.
df_entregas = conn.query("""SELECT [DocNum]
      ,[DocType]
      ,[DocStatus]
      ,[DocDate]
      ,[DocDueDate]
      ,[CardCode]
      ,[CardName]
      ,[DocTotal]
      ,[Comments]
      ,[LineStatus]
      ,[ItemCode]
      ,[ItemName]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[WhsCode]
  FROM [SBO_HELA].[dbo].[Z_VIEW_ENTREGAS_HISTORICO]""")

# df_pedidos: Detalle histórico de pedidos de clientes (órdenes de venta).
df_pedidos = conn.query("""SELECT 
      [DocEntry] 
      ,[NumPedido]
      ,[DocStatus]
      ,[DocDate]
      ,[DocDueDate]
      ,[NumAtCard]
      ,[CardCode]
      ,[CardName]
      ,[SlpCode]
      ,[SlpName]
      ,[DocCur]
      ,[GrosProfit] as Neto
      ,[VatPaid] as IVA
      ,[DocTotal] as Total
      ,[LineStatus]
      ,[U_ARTI_GRUPO]
      ,[ItemCode]
      ,[ItemName]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[QtyKilos]
  FROM [SBO_HELA].[dbo].[Z_VIEW_PEDIDOS_CLIENTES_HISTORICO]""")

# df_facturas: Detalle histórico de facturación a nivel de ítem.
df_facturas = conn.query("""SELECT  [DocEntry]
      ,[DocNum]
      ,[Tipo]
      ,[DocStatus]
      ,[DocDate]
      ,[DocDueDate]
      ,[CardCode]
      ,[CardName]
      ,[Neto]
      ,[Descuento]
      ,[IVA]
      ,[DocTotal]
      ,[Comments]
      ,[TrnspCode]
      ,[SlpCode]
      ,[SlpName]
      ,[TrnspName]
      ,[ItemCode]
      ,[ItemName]
      ,[unitMsr]
      ,[Quantity]
      ,[Price]
      ,[LineTotal]
      ,[CostoItem]
      ,[CostoInv]
      ,[CostoUnitInvt]
      ,[QuantityKg]
      ,[MargenEstablecido]
      ,[MargenReal]
      ,[PrecioSugeridoVenta]
      ,[PrecioSugeridoInvnt]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_HISTORICO]""")

# df_ventas_mes: Consolidado mensual de ventas netas por cliente.
df_ventas_mes = conn.query("""SELECT  [AñoMes]
      ,[CardName]
      ,[VentasNetas]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_CLIENTES_AÑO_MES]""")

# df_ventas_items_mes: Consolidado mensual de ventas netas por producto/ítem.
df_ventas_items_mes = conn.query("""SELECT  [AñoMes]
      ,[ItemName]
      ,[VentasNetas]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_ITEMS_AÑO_MES]""")

# df_ventas_vendedores_mes: Consolidado mensual de ventas netas por vendedor.
df_ventas_vendedores_mes = conn.query("""SELECT  [AñoMes]
      ,[SlpName]
      ,[VentasNetas]
  FROM [SBO_HELA].[dbo].[Z_VIEW_FACTURAS_VENTA_VENDEDORES_AÑO_MES]""")

# df_ventas_volumen_mensual: Volumen de ventas mensual para comparativos anuales.
df_ventas_volumen_mensual = conn.query("""SELECT [AñoMes]
      ,[VentasNetas]
  FROM [SBO_HELA].[dbo].[Z_VIEW_VENTAS_VOLUMEN_MENSUAL]""")

# df_okr: Indicadores de objetivos y resultados clave del periodo.
df_okr = conn.query("""SELECT  [Indicador]
      ,[ValorTexto]
      ,[ValorPorcentaje]
      ,[FechaEvaluacion]
      ,[Descripcion]
      ,[Area]
  FROM [SBO_HELA].[dbo].[Z_VIEW_OKR]""")

# df_kpi_precios: Análisis de precios por cliente (Target vs Real)
try:
    df_kpi_precios = conn.query("""SELECT  [CardName] as Cliente
          ,[mes]
          ,case when [precio_target] = 0 then 1 else [precio_target] end as precio_target
          , [precio_real]
          , case when [precio_target] in (0,1) then 100 else ((([precio_real] - [precio_target]) /  [precio_target])  * 100) end as delta
      FROM [SBO_HELA].[dbo].[Z_VIEW_KPI_CLIENTES_PRECIOS]
      order by mes""")
except Exception as e:
    st.error(f"⚠️ Error al cargar KPIs de Precios: {e}")
    df_kpi_precios = pd.DataFrame(columns=['Cliente', 'mes', 'precio_target', 'precio_real', 'delta'])

# -----------------------------------------------
# VOLUMEN DE VENTAS – Métricas principales
# -----------------------------------------------
st.markdown("### 💰 Volumen de Ventas")

# Preparar fechas de facturas
df_facturas['DocDate_DT'] = pd.to_datetime(df_facturas['DocDate'], errors='coerce')

# Versión del dataframe con documentos únicos para totales monetarios (evitar duplicidad por líneas)
df_facturas_doc = df_facturas.drop_duplicates('DocNum')

_hoy_vol = pd.Timestamp.today()
_año_hoy = _hoy_vol.year
_año_ant = _año_hoy - 1

_mask_ytd_u = (
    (df_facturas_doc['DocDate_DT'].dt.year == _año_hoy)
    & (df_facturas_doc['DocDate_DT'] <= _hoy_vol)
)
_ventas_ytd = df_facturas_doc.loc[_mask_ytd_u, 'DocTotal'].sum()

# --- Cálculo de Ventas Totales Año Actual vs Anterior Comparativo (mismo periodo) ---
df_ventas_volumen_mensual['Año'] = df_ventas_volumen_mensual['AñoMes'].astype(str).str[:4].astype(int)
df_ventas_volumen_mensual['Mes'] = df_ventas_volumen_mensual['AñoMes'].astype(str).str[4:].astype(int)
_mes_actual_limite = _hoy_vol.month

_ventas_total_actual = df_ventas_volumen_mensual[
    (df_ventas_volumen_mensual['Año'] == _año_hoy) & 
    (df_ventas_volumen_mensual['Mes'] <= _mes_actual_limite)
]['VentasNetas'].sum()

_ventas_total_anterior_comp = df_ventas_volumen_mensual[
    (df_ventas_volumen_mensual['Año'] == _año_ant) & 
    (df_ventas_volumen_mensual['Mes'] <= _mes_actual_limite)
]['VentasNetas'].sum()

_pct_variacion_anual = ((_ventas_total_actual - _ventas_total_anterior_comp) / _ventas_total_anterior_comp * 100) if _ventas_total_anterior_comp != 0 else 0

# --- H1 actual y H1 año anterior (para delta ventas) ---
_mask_h1_actual_u = (
    (df_facturas_doc['DocDate_DT'].dt.year == _año_hoy)
    & (df_facturas_doc['DocDate_DT'].dt.month <= 6)
)
_mask_h1_anterior_u = (
    (df_facturas_doc['DocDate_DT'].dt.year == _año_ant)
    & (df_facturas_doc['DocDate_DT'].dt.month <= 6)
)
_ventas_h1_actual = df_facturas_doc.loc[_mask_h1_actual_u, 'DocTotal'].sum()
_ventas_h1_anterior = df_facturas_doc.loc[_mask_h1_anterior_u, 'DocTotal'].sum()
_delta_ventas_pct = ((_ventas_h1_actual - _ventas_h1_anterior) / _ventas_h1_anterior * 100) if _ventas_h1_anterior != 0 else 0

# --- Kilos H1 actual y H1 año anterior (se suma sobre el detalle completo de líneas) ---
_mask_h1_actual = (
    (df_facturas['DocDate_DT'].dt.year == _año_hoy)
    & (df_facturas['DocDate_DT'].dt.month <= 6)
)
_mask_h1_anterior = (
    (df_facturas['DocDate_DT'].dt.year == _año_ant)
    & (df_facturas['DocDate_DT'].dt.month <= 6)
)
_kilos_h1_actual = df_facturas.loc[_mask_h1_actual, 'QuantityKg'].sum()
_kilos_h1_anterior = df_facturas.loc[_mask_h1_anterior, 'QuantityKg'].sum()
_delta_kilos_pct = ((_kilos_h1_actual - _kilos_h1_anterior) / _kilos_h1_anterior * 100) if _kilos_h1_anterior != 0 else 0

# --- Lógica Ventas Mes Actual vs Anterior ---
try:
    # Convertimos AñoMes (ej: 202404) a datetime para ordenar correctamente
    df_ventas_mes['periodo_dt'] = pd.to_datetime(df_ventas_mes['AñoMes'].astype(str), format='%Y%m', errors='coerce')
    _df_mensual_agrupado = df_ventas_mes.groupby('periodo_dt')['VentasNetas'].sum().reset_index().sort_values('periodo_dt')

    if len(_df_mensual_agrupado) >= 1:
        _v_mes_actual = _df_mensual_agrupado.iloc[-1]['VentasNetas']
        _label_mes_actual = _df_mensual_agrupado.iloc[-1]['periodo_dt'].strftime("%b %Y")
        
        if len(_df_mensual_agrupado) >= 2:
            _v_mes_anterior = _df_mensual_agrupado.iloc[-2]['VentasNetas']
        else:
            _v_mes_anterior = 0
            
        _diff_mes = _v_mes_actual - _v_mes_anterior
        _pct_mes = (_diff_mes / _v_mes_anterior * 100) if _v_mes_anterior != 0 else 0
    else:
        _v_mes_actual = 0
        _label_mes_actual = "Sin datos"
        _diff_mes = 0
        _pct_mes = 0
except Exception:
    _v_mes_actual = 0
    _label_mes_actual = "Error"
    _diff_mes = 0
    _pct_mes = 0

# Formatear valores grandes (M$1.5)
def fmt_m(val):
    if abs(val) >= 1_000_000:
        return f"M${val/1_000_000:,.1f}"
    elif abs(val) >= 1_000:
        return f"${val/1_000:,.0f}K"
    return f"${val:,.0f}"

def fmt_kg(val):
    if abs(val) >= 1_000_000:
        return f"M{val/1_000_000:,.1f} kg"
    elif abs(val) >= 1_000:
        return f"{val/1_000:,.1f}K kg"
    return f"{val:,.0f} kg"

col_v3, col_v5 = st.columns(2)
col_v3.metric(
    f"💰 Ventas Totales Año {_año_hoy}",
    fmt_m(_ventas_total_actual),
    delta=f"{_pct_variacion_anual:+.1f}% vs mismo periodo {_año_ant}",
)
col_v5.metric(
    f"📅 Ventas {_label_mes_actual}",
    fmt_m(_v_mes_actual),
    delta=f"{_pct_mes:+.1f}% vs mes ant.",
)

# -----------------------------------------------
# RANKING DE VENTAS POR VENDEDOR
# -----------------------------------------------
st.markdown("---")
st.markdown("### 🏆 Ranking de Ventas por Vendedor")

# Preparar datos: convertir AñoMes a datetime para filtrado
df_ventas_vendedores_mes['periodo_dt'] = pd.to_datetime(
    df_ventas_vendedores_mes['AñoMes'].astype(str), format='%Y%m', errors='coerce'
)

# Rango de fechas por defecto: 1-Ene del año actual → hoy
_fecha_min_vendedores = pd.Timestamp(f'{_año_hoy}-01-01').date()
_fecha_max_vendedores = pd.Timestamp.today().date()

col_fecha_ini, col_fecha_fin = st.columns(2)
with col_fecha_ini:
    _rango_inicio = st.date_input(
        "📅 Desde",
        value=_fecha_min_vendedores,
        min_value=df_ventas_vendedores_mes['periodo_dt'].min().date() if not df_ventas_vendedores_mes.empty else _fecha_min_vendedores,
        max_value=_fecha_max_vendedores,
        key="ranking_fecha_inicio",
    )
with col_fecha_fin:
    _rango_fin = st.date_input(
        "📅 Hasta",
        value=_fecha_max_vendedores,
        min_value=df_ventas_vendedores_mes['periodo_dt'].min().date() if not df_ventas_vendedores_mes.empty else _fecha_min_vendedores,
        max_value=_fecha_max_vendedores,
        key="ranking_fecha_fin",
    )

# Filtrar el dataframe por rango seleccionado
_mask_rango_vendedores = (
    (df_ventas_vendedores_mes['periodo_dt'].dt.date >= _rango_inicio)
    & (df_ventas_vendedores_mes['periodo_dt'].dt.date <= _rango_fin)
)
df_ranking_vendedores = (
    df_ventas_vendedores_mes.loc[_mask_rango_vendedores]
    .groupby('SlpName', as_index=False)['VentasNetas']
    .sum()
    .sort_values('VentasNetas', ascending=True)  # ascendente para que el mayor quede arriba en barh
)

if not df_ranking_vendedores.empty:
    # Escala de colores proporcional al valor
    _max_venta = df_ranking_vendedores['VentasNetas'].max()
    _colores = [
        f'rgba(59,130,246,{0.35 + 0.65 * (v / _max_venta)})' for v in df_ranking_vendedores['VentasNetas']
    ]

    fig_ranking = go.Figure(
        go.Bar(
            x=df_ranking_vendedores['VentasNetas'],
            y=df_ranking_vendedores['SlpName'],
            orientation='h',
            marker=dict(color=_colores, line=dict(width=0)),
            text=df_ranking_vendedores['VentasNetas'].apply(fmt_m),
            textposition='outside',
            textfont=dict(size=12, color='#e2e8f0'),
            hovertemplate='<b>%{y}</b><br>Ventas: %{x:$,.0f}<extra></extra>',
        )
    )

    fig_ranking.update_layout(
        title=dict(
            text=f'Ventas acumuladas por vendedor  ·  {_rango_inicio.strftime("%d/%m/%Y")} – {_rango_fin.strftime("%d/%m/%Y")}',
            font=dict(size=15),
        ),
        xaxis=dict(
            title='Ventas Netas',
            showgrid=True,
            gridcolor='rgba(128,128,128,0.15)',
            zeroline=False,
        ),
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

# --- SECCIÓN: ANÁLISIS DE PRECIOS ---
st.markdown("---")
st.markdown("### 📊 Evolución de Precios Target vs Real")

# Filtro multiselect para años (2022 al 2026)
_años_disponibles = [2022, 2023, 2024, 2025, 2026]
años_seleccionados = st.multiselect(
    "Filtrar por Año:",
    options=_años_disponibles,
    default=[2024, 2025, 2026]
)

if años_seleccionados:
    # Preparar el dataframe: Extraer año de 'mes' (asumiendo formato YYYYMM)
    df_kpi_precios['año'] = df_kpi_precios['mes'].astype(str).str[:4].astype(int)
    
    # Filtrar datos por los años seleccionados
    df_precios_filt = df_kpi_precios[df_kpi_precios['año'].isin(años_seleccionados)].copy()
    
    if not df_precios_filt.empty:
        # Agrupar datos por mes para visualizar la tendencia promedio del Delta
        df_chart_precios = df_precios_filt.groupby('mes')[['delta']].mean()
        
        if not df_chart_precios.empty:
            # Crear gráfico avanzado con Plotly para marcar máximos y mínimos
            fig_delta = go.Figure()
            
            # Línea principal
            fig_delta.add_trace(go.Scatter(
                x=df_chart_precios.index, 
                y=df_chart_precios['delta'],
                mode='lines+markers',
                name='Promedio Delta',
                line=dict(color='#3b82f6', width=2),
                marker=dict(size=6)
            ))
            
            # Identificar puntos extremos
            idx_min = df_chart_precios['delta'].idxmin()
            val_min = df_chart_precios['delta'].min()
            idx_max = df_chart_precios['delta'].idxmax()
            val_max = df_chart_precios['delta'].max()
            
            # Punto Rojo (Mínimo) - Solo si es menor a cero
            if val_min < 0:
                fig_delta.add_trace(go.Scatter(
                    x=[idx_min], y=[val_min],
                    mode='markers',
                    marker=dict(color='red', size=12),
                    name='Mínimo (Negativo)'
                ))
            
            # Punto Verde (Máximo)
            fig_delta.add_trace(go.Scatter(
                x=[idx_max], y=[val_max],
                mode='markers',
                marker=dict(color='green', size=12),
                name='Máximo Histórico'
            ))
            
            fig_delta.update_layout(
                title='Tendencia Mensual del Delta (%)',
                xaxis_title='Mes (AñoMes)',
                yaxis_title='Delta %',
                hovermode='x unified',
                height=400,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            st.plotly_chart(fig_delta, use_container_width=True)
        else:
            st.info("Sin datos para graficar.")
    else:
        st.info("No hay datos disponibles para los años seleccionados.")
else:
    st.warning("Seleccione al menos un año para visualizar la gráfica.")
