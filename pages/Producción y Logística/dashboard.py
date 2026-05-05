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

st.title("Panel de Control Producción y Logística")
st.write("Bienvenido al dashboard central de factores operativos.")

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

# df_okr: Indicadores de objetivos y resultados clave del periodo.
df_okr = conn.query("""SELECT  [Indicador]
      ,[ValorTexto]
      ,[ValorPorcentaje]
      ,[FechaEvaluacion]
      ,[Descripcion]
      ,[Area]
  FROM [SBO_HELA].[dbo].[Z_VIEW_OKR]""")

# -----------------------------------------------
# CRUCE DE DATOS: ENTREGAS Y PEDIDOS
# -----------------------------------------------

# Preparar DataFrame de Pedidos (PE_)
df_pe = df_pedidos[['NumPedido', 'DocDate', 'DocDueDate', 'Total', 'ItemCode', 'Quantity', 'LineTotal']].copy()
df_pe = df_pe.rename(columns={
    'NumPedido': 'PE_DocNum',
    'DocDate': 'PE_DocDate',
    'DocDueDate': 'PE_DocDueDate',
    'Total': 'PE_DocTotal',
    'ItemCode': 'ItemCode_Join', # Usaremos ItemCode cruzado
    'Quantity': 'PE_Quantity',
    'LineTotal': 'PE_LineTotal'
})
# Casteo numérico de clave
df_pe['PE_DocNum_Join'] = pd.to_numeric(df_pe['PE_DocNum'], errors='coerce').fillna(-2).astype(int)


# Preparar DataFrame de Entregas (EN_)
df_en = df_entregas[['DocNum', 'DocDate', 'DocDueDate', 'DocTotal', 'Comments', 'ItemCode', 'Quantity', 'LineTotal']].copy()
df_en = df_en.rename(columns={
    'DocNum': 'EN_DocNum',
    'DocDate': 'EN_DocDate',
    'DocDueDate': 'EN_DocDueDate',
    'DocTotal': 'EN_DocTotal',
    'ItemCode': 'ItemCode_Join', 
    'Quantity': 'EN_Quantity',
    'LineTotal': 'EN_LineTotal'
})
# Extraer el primer bloque numérico dentro de los Comments (Asumiendo que es el pedido)
df_en['EN_Ref_Pedido_Join'] = df_en['Comments'].astype(str).str.extract(r'(\d+)').fillna(-1).astype(int)


# Realizar JOIN de Entregas -> Pedidos (por N° Pedido cruzado + Artículo)
df_cruce = pd.merge(
    df_en, 
    df_pe, 
    left_on=['EN_Ref_Pedido_Join', 'ItemCode_Join'], 
    right_on=['PE_DocNum_Join', 'ItemCode_Join'], 
    how='inner' 
)

# Renombrar ItemCode unificado y limpiar las claves temporales
df_cruce = df_cruce.rename(columns={'ItemCode_Join': 'ItemCode'})
df_cruce = df_cruce.drop(columns=['EN_Ref_Pedido_Join', 'PE_DocNum_Join', 'Comments'])

# Reordenar las columnas visualmente intercaladas para ser más amigable
columns_order = [
    'ItemCode',
    'EN_DocNum', 'PE_DocNum',
    'EN_DocDate', 'PE_DocDate',
    'EN_Quantity', 'PE_Quantity',
    'EN_LineTotal', 'PE_LineTotal',
    'EN_DocTotal', 'PE_DocTotal',
    'EN_DocDueDate', 'PE_DocDueDate'
]
# Sólo por precaución filtramos aquellas que existan si falló algo
columns_order = [col for col in columns_order if col in df_cruce.columns]
df_cruce = df_cruce[columns_order]

# Conversiones numéricas y de fecha seguras para cálculos
df_cruce['EN_DueDate_DT'] = pd.to_datetime(df_cruce['EN_DocDueDate'], errors='coerce')
df_cruce['PE_DueDate_DT'] = pd.to_datetime(df_cruce['PE_DocDueDate'], errors='coerce')

df_cruce['EN_LineTotal_Num'] = pd.to_numeric(df_cruce['EN_LineTotal'], errors='coerce').fillna(0)
df_cruce['PE_LineTotal_Num'] = pd.to_numeric(df_cruce['PE_LineTotal'], errors='coerce').fillna(0)

# -----------------------------------------------
# LEAD TIME – Tiempo total de ciclo del pedido
# -----------------------------------------------
# Lead Time   = DocDueDate (entrega) - DocDate (pedido)
#               → Días desde que el cliente coloca el pedido hasta que
#                 recibe el producto.
# Días Atrasado = DocDueDate (entrega) - DocDueDate (pedido)
#               → Diferencia contra la fecha comprometida.
#                 Positivo = entrega tarde | Negativo = entrega adelantada

# Convertir fechas necesarias (EN_DueDate_DT y PE_DueDate_DT ya existen)
df_cruce['PE_DocDate_DT'] = pd.to_datetime(df_cruce['PE_DocDate'], errors='coerce')

# Construir DataFrame de Lead Time a nivel línea (ItemCode)
df_cruce['Lead_Time_Dias'] = (df_cruce['EN_DueDate_DT'] - df_cruce['PE_DocDate_DT']).dt.days
df_cruce['Dias_Atrasado']  = (df_cruce['EN_DueDate_DT'] - df_cruce['PE_DueDate_DT']).dt.days

# Agrupar a nivel documento (un pedido puede tener varias líneas de artículos)
df_leadtime = df_cruce.groupby(['PE_DocNum', 'EN_DocNum']).agg(
    Fecha_Pedido=('PE_DocDate_DT', 'first'),
    Fecha_Compromiso=('PE_DueDate_DT', 'first'),
    Fecha_Entrega=('EN_DueDate_DT', 'first'),
    Lead_Time=('Lead_Time_Dias', 'first'),
    Dias_Atrasado=('Dias_Atrasado', 'first'),
    Cant_Items=('ItemCode', 'nunique'),
).reset_index()

# Renombrar columnas para presentación
df_leadtime = df_leadtime.rename(columns={
    'PE_DocNum': 'Nro Pedido',
    'EN_DocNum': 'Nro Entrega',
    'Cant_Items': 'Items',
})

# --- Métricas OKR de Lead Time (sin filtro, mes actual) ---
try:
    META_LEADTIME_DIAS = int(df_okr.loc[df_okr['Indicador'] == 'LEADTIME', 'ValorTexto'].values[0])
except:
    META_LEADTIME_DIAS = 20  # Fallback por defecto si hay error en la carga

_hoy = pd.Timestamp.today()
_mes_actual = _hoy.month
_año_actual = _hoy.year
_mes_anterior = _mes_actual - 1 if _mes_actual > 1 else 12
_año_mes_anterior = _año_actual if _mes_actual > 1 else _año_actual - 1

# Calcular Lead Time promedio del mes actual y mes anterior
_lt_mes_actual = df_leadtime.loc[
    (df_leadtime['Fecha_Entrega'].dt.month == _mes_actual) &
    (df_leadtime['Fecha_Entrega'].dt.year == _año_actual),
    'Lead_Time'
].mean()

_lt_mes_anterior = df_leadtime.loc[
    (df_leadtime['Fecha_Entrega'].dt.month == _mes_anterior) &
    (df_leadtime['Fecha_Entrega'].dt.year == _año_mes_anterior),
    'Lead_Time'
].mean()

_lt_delta = None
if pd.notna(_lt_mes_actual) and pd.notna(_lt_mes_anterior):
    _lt_delta = round(_lt_mes_actual - _lt_mes_anterior, 1)

# Cálculo de cumplimiento vs Meta OKR
_pct_cumplimiento_lt = (META_LEADTIME_DIAS / _lt_mes_actual * 100) if pd.notna(_lt_mes_actual) and _lt_mes_actual > 0 else 0
_diff_vs_meta = _lt_mes_actual - META_LEADTIME_DIAS if pd.notna(_lt_mes_actual) else None


st.markdown("### ⏱️ Lead Time")

col_okr_lt1, col_okr_lt2, col_okr_lt3, _ = st.columns(4)
col_okr_lt1.metric(
    "🎯 GOAL (30/Jun/2026)",
    f"{META_LEADTIME_DIAS} días",
    delta="0",
)
col_okr_lt2.metric(
    f"📊 Lead Time Promedio — {_hoy.strftime('%B %Y').capitalize()}",
    f"{_lt_mes_actual:.1f} días" if pd.notna(_lt_mes_actual) else "Sin datos",
    delta=f"{_lt_delta:+.1f} días vs mes ant." if _lt_delta is not None else None,
    delta_color="inverse",
)
col_okr_lt3.metric(
    "✅ Cumplimiento Meta OKR",
    f"{_pct_cumplimiento_lt:.1f}%",
    delta=f"{_diff_vs_meta:+.1f} días vs meta" if _diff_vs_meta is not None else None,
    delta_color="inverse", # Más días es peor (rojo si es (+) )
)

# Formatear fechas para visualización (después de calcular métricas)
for col_fecha in ['Fecha_Pedido', 'Fecha_Compromiso', 'Fecha_Entrega']:
    df_leadtime[col_fecha] = pd.to_datetime(df_leadtime[col_fecha], errors='coerce').dt.strftime('%d/%m/%Y')

# Ordenar por días atrasado descendente (los más atrasados primero)
df_leadtime = df_leadtime.sort_values('Dias_Atrasado', ascending=False).reset_index(drop=True)

# Estilo condicional: rojo si atrasado (>0), verde si a tiempo (<=0)
def color_atraso(val):
    if pd.isna(val):
        return ''
    if val > 0:
        return 'color: #e74c3c; font-weight: bold'  # rojo
    elif val == 0:
        return 'color: #2ecc71; font-weight: bold'  # verde
    else:
        return 'color: #27ae60'  # verde oscuro (adelantado)

with st.expander("📋 Detalle Lead Time por Pedido", expanded=False):
    st.caption("Lead Time = días desde la fecha del pedido hasta la fecha de entrega  |  Días Atrasado = entrega vs fecha comprometida (positivo = tarde)")

    # KPIs de Lead Time
    lt_mean = df_leadtime['Lead_Time'].mean()
    lt_median = df_leadtime['Lead_Time'].median()
    atraso_mean = df_leadtime['Dias_Atrasado'].mean()
    pct_a_tiempo = (df_leadtime['Dias_Atrasado'] <= 0).sum() / len(df_leadtime) * 100 if len(df_leadtime) > 0 else 0

    col_lt1, col_lt2, col_lt3, col_lt4 = st.columns(4)
    col_lt1.metric("Lead Time Promedio", f"{lt_mean:.1f} días")
    col_lt2.metric("Lead Time Mediana", f"{lt_median:.0f} días")
    col_lt3.metric("Atraso Promedio", f"{atraso_mean:+.1f} días")
    col_lt4.metric("% A Tiempo", f"{pct_a_tiempo:.1f}%")

    # Mostrar tabla con estilo
    st.dataframe(
        df_leadtime.style.applymap(color_atraso, subset=['Dias_Atrasado']),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------------------------
# CÁLCULO OTIF – Preparación de DataFrames
# -----------------------------------------------

st.markdown("### 📊 Indicador OTIF (On Time In Full)")

# --- 1. DataFrame de Pedidos para OTIF ---
col_fecha_compromiso = 'ShipDate' if 'ShipDate' in df_pedidos.columns else 'DocDueDate'

df_pedidos_otif = df_pedidos[['NumPedido', 'ItemCode', 'DocDate', col_fecha_compromiso, 'Quantity']].copy()
df_pedidos_otif['pedido_id'] = df_pedidos_otif['NumPedido'].astype(str) + '-' + df_pedidos_otif['ItemCode'].astype(str)
df_pedidos_otif = df_pedidos_otif.rename(columns={
    'DocDate': 'fecha_pedido',
    col_fecha_compromiso: 'fecha_entrega_comprometida',
    'Quantity': 'cantidad_pedida',
})
df_pedidos_otif['fecha_pedido'] = pd.to_datetime(df_pedidos_otif['fecha_pedido'], errors='coerce')
df_pedidos_otif['fecha_entrega_comprometida'] = pd.to_datetime(df_pedidos_otif['fecha_entrega_comprometida'], errors='coerce')

df_pedidos_otif = df_pedidos_otif.groupby('pedido_id').agg(
    fecha_pedido=('fecha_pedido', 'first'),
    fecha_entrega_comprometida=('fecha_entrega_comprometida', 'first'),
    cantidad_pedida=('cantidad_pedida', 'sum'),
).reset_index()

# --- 2. DataFrame de Entregas para OTIF ---
df_entregas_otif = df_entregas[['DocNum', 'ItemCode', 'DocDate', 'Quantity', 'Comments']].copy()
df_entregas_otif['ref_pedido'] = df_entregas_otif['Comments'].astype(str).str.extract(r'(\d+)')
df_entregas_otif['pedido_id'] = df_entregas_otif['ref_pedido'].astype(str) + '-' + df_entregas_otif['ItemCode'].astype(str)
df_entregas_otif['entrega_id'] = df_entregas_otif['DocNum'].astype(str) + '-' + df_entregas_otif['ItemCode'].astype(str)
df_entregas_otif = df_entregas_otif.rename(columns={
    'DocDate': 'fecha_entrega_real',
    'Quantity': 'cantidad_entregada',
})

lookup_qty = df_pedidos_otif.set_index('pedido_id')['cantidad_pedida']
entregas_acum = df_entregas_otif.groupby('pedido_id')['cantidad_entregada'].transform('sum')
qty_pedida_map = df_entregas_otif['pedido_id'].map(lookup_qty)
df_entregas_otif['estado_entrega'] = np.where(entregas_acum >= qty_pedida_map, 'completa', 'parcial')
df_entregas_otif['estado_entrega'] = df_entregas_otif['estado_entrega'].fillna('parcial')

df_pedidos_otif = df_pedidos_otif[['pedido_id', 'fecha_pedido', 'fecha_entrega_comprometida', 'cantidad_pedida']]
df_entregas_otif = df_entregas_otif[['entrega_id', 'pedido_id', 'fecha_entrega_real', 'cantidad_entregada', 'estado_entrega']]
df_entregas_otif = df_entregas_otif[df_entregas_otif['pedido_id'].str.contains(r'^\d+', regex=True, na=False)]

# Años disponibles para filtros
_años_disponibles = sorted(df_pedidos_otif['fecha_pedido'].dt.year.dropna().unique().astype(int).tolist())
if not _años_disponibles:
    _años_disponibles = [2022, 2023, 2024, 2025, 2026]

# --- Métricas OKR de OTIF (sin filtro, mes actual) ---
META_OTIF_PCT = 80  # Meta OKR semestral en % (al 30/Jun/2026)

# Calcular OTIF del mes actual y anterior SIN filtro
try:
    _otif_global = calcular_otif(
        df_pedidos_otif, df_entregas_otif,
        periodo='mensual', tolerancia_dias=1, tolerancia_cantidad_pct=0.02,
    )
    _resumen_global = _otif_global['resumen']
    # Construir label del mes actual y anterior
    _label_mes_actual = f"{_año_actual}-{_mes_actual:02d}"
    _label_mes_anterior = f"{_año_mes_anterior}-{_mes_anterior:02d}"
    _otif_actual = _resumen_global.loc[_resumen_global['periodo_label'] == _label_mes_actual, 'pct_otif']
    _otif_anterior = _resumen_global.loc[_resumen_global['periodo_label'] == _label_mes_anterior, 'pct_otif']
    _otif_actual_val = _otif_actual.values[0] if len(_otif_actual) > 0 else None
    _otif_anterior_val = _otif_anterior.values[0] if len(_otif_anterior) > 0 else None
    _otif_delta = round(_otif_actual_val - _otif_anterior_val, 1) if _otif_actual_val is not None and _otif_anterior_val is not None else None
except Exception:
    _otif_actual_val = None
    _otif_delta = None

col_okr_ot1, col_okr_ot2, _, _ = st.columns(4)
col_okr_ot1.metric(
    "🎯 GOAL (30/Jun/2026)",
    f"{META_OTIF_PCT}%",
    delta="+10%",
)
col_okr_ot2.metric(
    f"📊 OTIF — {_hoy.strftime('%B %Y').capitalize()}",
    f"{_otif_actual_val:.1f}%" if _otif_actual_val is not None else "Sin datos",
    delta=f"{_otif_delta:+.1f}% vs mes ant." if _otif_delta is not None else None,
)

with st.expander("📋 Detalle Indicador OTIF", expanded=False):

    col_filtro_tipo, col_filtro_ctrl = st.columns([1, 3])

    with col_filtro_tipo:
        tipo_filtro = st.selectbox(
            "Filtrar por:",
            ["Por Año", "Por Año-Trimestre", "Rango de Fechas"],
            key="otif_tipo_filtro",
        )

    with col_filtro_ctrl:
        if tipo_filtro == "Por Año":
            años_sel = st.multiselect(
                "Seleccionar Años:",
                options=_años_disponibles,
                default=_años_disponibles,
                key="otif_años",
            )
            if años_sel:
                mask_pedidos = df_pedidos_otif['fecha_pedido'].dt.year.isin(años_sel)
                df_pedidos_otif = df_pedidos_otif[mask_pedidos]
                pedidos_validos = set(df_pedidos_otif['pedido_id'])
                df_entregas_otif = df_entregas_otif[df_entregas_otif['pedido_id'].isin(pedidos_validos)]

        elif tipo_filtro == "Por Año-Trimestre":
            col_anio_q, col_trim_q = st.columns(2)
            with col_anio_q:
                año_q = st.selectbox("Año:", options=_años_disponibles, index=len(_años_disponibles) - 1, key="otif_año_q")
            with col_trim_q:
                trim_q = st.multiselect(
                    "Trimestre:",
                    options=["Q1 (Ene-Mar)", "Q2 (Abr-Jun)", "Q3 (Jul-Sep)", "Q4 (Oct-Dic)"],
                    default=["Q1 (Ene-Mar)", "Q2 (Abr-Jun)", "Q3 (Jul-Sep)", "Q4 (Oct-Dic)"],
                    key="otif_trim_q",
                )
            _trim_meses = {
                "Q1 (Ene-Mar)": [1, 2, 3], "Q2 (Abr-Jun)": [4, 5, 6],
                "Q3 (Jul-Sep)": [7, 8, 9], "Q4 (Oct-Dic)": [10, 11, 12],
            }
            meses_sel = []
            for t in trim_q:
                meses_sel.extend(_trim_meses.get(t, []))
            if meses_sel:
                mask_pedidos = (
                    (df_pedidos_otif['fecha_pedido'].dt.year == año_q)
                    & (df_pedidos_otif['fecha_pedido'].dt.month.isin(meses_sel))
                )
                df_pedidos_otif = df_pedidos_otif[mask_pedidos]
                pedidos_validos = set(df_pedidos_otif['pedido_id'])
                df_entregas_otif = df_entregas_otif[df_entregas_otif['pedido_id'].isin(pedidos_validos)]

        elif tipo_filtro == "Rango de Fechas":
            _min_date = df_pedidos_otif['fecha_pedido'].min()
            _max_date = df_pedidos_otif['fecha_pedido'].max()
            if pd.isna(_min_date):
                _min_date = pd.Timestamp('2022-01-01')
            if pd.isna(_max_date):
                _max_date = pd.Timestamp.today()
            rango = st.date_input(
                "Rango de fechas:",
                value=(_min_date.date(), _max_date.date()),
                min_value=_min_date.date(),
                max_value=_max_date.date(),
                key="otif_rango",
            )
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                fecha_ini, fecha_fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
                mask_pedidos = (
                    (df_pedidos_otif['fecha_pedido'] >= fecha_ini)
                    & (df_pedidos_otif['fecha_pedido'] <= fecha_fin)
                )
                df_pedidos_otif = df_pedidos_otif[mask_pedidos]
                pedidos_validos = set(df_pedidos_otif['pedido_id'])
                df_entregas_otif = df_entregas_otif[df_entregas_otif['pedido_id'].isin(pedidos_validos)]

    st.caption(f"📌 Pedidos en el rango seleccionado: **{len(df_pedidos_otif):,}**")

    try:
        resultado_otif = calcular_otif(
            df_pedidos_otif,
            df_entregas_otif,
            periodo='mensual',
            tolerancia_dias=1,
            tolerancia_cantidad_pct=0.02,
        )

        meta = resultado_otif['metadata']

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Pedidos", f"{meta['total_pedidos']:,}")
        col2.metric("On Time %", f"{meta['pct_on_time_global']:.1f}%")
        col3.metric("In Full %", f"{meta['pct_in_full_global']:.1f}%")
        col4.metric("OTIF %", f"{meta['pct_otif_global']:.1f}%")

        st.markdown("#### Resumen OTIF por Periodo")
        df_resumen = resultado_otif['resumen']
        df_resumen_show = df_resumen.rename(columns={
            'periodo_label': 'Periodo',
            'total_pedidos': 'Pedidos',
            'pct_on_time': 'On Time %',
            'pct_in_full': 'In Full %',
            'pct_otif': 'OTIF %',
        })
        st.dataframe(
            df_resumen_show[['Periodo', 'Pedidos', 'On Time %', 'In Full %', 'OTIF %']],
            use_container_width=True,
            hide_index=True,
        )

        if len(df_resumen) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_resumen['periodo_label'], y=df_resumen['pct_on_time'],
                name='On Time %', mode='lines+markers',
                line=dict(color='#36b5d8', width=2),
            ))
            fig.add_trace(go.Scatter(
                x=df_resumen['periodo_label'], y=df_resumen['pct_in_full'],
                name='In Full %', mode='lines+markers',
                line=dict(color='#f0a500', width=2),
            ))
            fig.add_trace(go.Scatter(
                x=df_resumen['periodo_label'], y=df_resumen['pct_otif'],
                name='OTIF %', mode='lines+markers',
                line=dict(color='#2ecc71', width=3),
            ))
            fig.update_layout(
                title='Evolución OTIF Mensual',
                xaxis_title='Periodo',
                yaxis_title='Porcentaje (%)',
                yaxis=dict(range=[0, 105]),
                template='plotly_white',
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Ver detalle por pedido"):
            df_detalle = resultado_otif['detalle']
            cols_detalle = [
                'pedido_id', 'fecha_entrega_comprometida', 'fecha_entrega_real',
                'cantidad_pedida', 'cantidad_entregada', 'n_entregas',
                'flag_on_time', 'flag_in_full', 'flag_otif',
                'dias_desviacion', 'pct_cantidad',
            ]
            cols_detalle = [c for c in cols_detalle if c in df_detalle.columns]
            st.dataframe(df_detalle[cols_detalle], use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # ANÁLISIS PARETO – Incumplimientos por Cliente y Producto
        # ---------------------------------------------------------
        df_detalle = resultado_otif['detalle'].copy()
        df_detalle['_DocNum'] = df_detalle['pedido_id'].str.split('-').str[0]
        df_detalle['_ItemCode'] = df_detalle['pedido_id'].str.split('-', n=1).str[1]

        lookup_cliente = df_pedidos.drop_duplicates(subset='NumPedido')[['NumPedido', 'CardName']].copy()
        lookup_cliente['NumPedido'] = lookup_cliente['NumPedido'].astype(str)
        df_detalle = df_detalle.merge(lookup_cliente, left_on='_DocNum', right_on='NumPedido', how='left')

        lookup_producto = df_pedidos.drop_duplicates(subset='ItemCode')[['ItemCode', 'ItemName']].copy()
        lookup_producto = lookup_producto.rename(columns={'ItemName': 'Dscription'})
        lookup_producto['ItemCode'] = lookup_producto['ItemCode'].astype(str)
        df_detalle = df_detalle.merge(lookup_producto, left_on='_ItemCode', right_on='ItemCode', how='left')

        df_detalle['CardName'] = df_detalle['CardName'].fillna(df_detalle['_DocNum'])
        df_detalle['Dscription'] = df_detalle['Dscription'].fillna(df_detalle['_ItemCode'])

        df_not_ot = df_detalle[df_detalle['flag_on_time'] == False]
        df_not_if = df_detalle[df_detalle['flag_in_full'] == False]

        def sumarizar(df_src, group_col, label_col, umbral=5):
            if df_src.empty:
                return pd.DataFrame(columns=[label_col, 'Incumplimientos', 'Acumulado %'])
            conteo = df_src.groupby(group_col).size().reset_index(name='Incumplimientos')
            conteo = conteo.sort_values('Incumplimientos', ascending=False).reset_index(drop=True)
            conteo = conteo.rename(columns={group_col: label_col})
            mask_otros = conteo['Incumplimientos'] <= umbral
            if mask_otros.any():
                prom_otros = round(conteo.loc[mask_otros, 'Incumplimientos'].mean())
                conteo = conteo[~mask_otros].reset_index(drop=True)
                fila_otros = pd.DataFrame({label_col: ['Otros'], 'Incumplimientos': [prom_otros]})
                conteo = pd.concat([conteo, fila_otros], ignore_index=True)
            conteo['Acumulado %'] = (conteo['Incumplimientos'].cumsum() / conteo['Incumplimientos'].sum() * 100).round(1)
            return conteo

        df_ot_cliente = sumarizar(df_not_ot, 'CardName', 'Cliente')
        df_if_cliente = sumarizar(df_not_if, 'CardName', 'Cliente')
        df_ot_producto = sumarizar(df_not_ot, 'Dscription', 'Producto')
        df_if_producto = sumarizar(df_not_if, 'Dscription', 'Producto')

        def pareto_chart(df_sum, label_col, title, color_bar):
            if df_sum.empty:
                st.info(f"Sin incumplimientos para: {title}")
                return
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(x=df_sum[label_col], y=df_sum['Incumplimientos'],
                       name='Incumplimientos', marker_color=color_bar, opacity=0.85),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=df_sum[label_col], y=df_sum['Acumulado %'],
                           name='Acumulado %', mode='lines+markers',
                           line=dict(color='#e74c3c', width=2)),
                secondary_y=True,
            )
            fig.update_layout(
                title=title,
                xaxis=dict(tickangle=-45),
                yaxis=dict(title='Cantidad'),
                yaxis2=dict(title='Acumulado %', range=[0, 105]),
                template='plotly_white',
                height=420,
                showlegend=True,
                legend=dict(orientation='h', y=1.12),
                margin=dict(b=120),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📉 Análisis Pareto de Incumplimientos OTIF")

        def filtrar_top20(df_sum):
            n_top = max(1, int(len(df_sum) * 0.2))
            return df_sum.head(n_top).reset_index(drop=True)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            solo_top_ot_cli = st.toggle("Solo Top 20%", key="top20_ot_cli", value=False)
            df_show = filtrar_top20(df_ot_cliente) if solo_top_ot_cli else df_ot_cliente
            pareto_chart(df_show, 'Cliente', '❌ No On Time – por Cliente', '#e67e22')
            with st.expander("📋 Tabla: No On Time por Cliente"):
                st.dataframe(df_show, use_container_width=True, hide_index=True)
        with col_p2:
            solo_top_if_cli = st.toggle("Solo Top 20%", key="top20_if_cli", value=False)
            df_show = filtrar_top20(df_if_cliente) if solo_top_if_cli else df_if_cliente
            pareto_chart(df_show, 'Cliente', '❌ No In Full – por Cliente', '#9b59b6')
            with st.expander("📋 Tabla: No In Full por Cliente"):
                st.dataframe(df_show, use_container_width=True, hide_index=True)

        col_p3, col_p4 = st.columns(2)
        with col_p3:
            solo_top_ot_prod = st.toggle("Solo Top 20%", key="top20_ot_prod", value=False)
            df_show = filtrar_top20(df_ot_producto) if solo_top_ot_prod else df_ot_producto
            pareto_chart(df_show, 'Producto', '❌ No On Time – por Producto', '#e74c3c')
            with st.expander("📋 Tabla: No On Time por Producto"):
                st.dataframe(df_show, use_container_width=True, hide_index=True)
        with col_p4:
            solo_top_if_prod = st.toggle("Solo Top 20%", key="top20_if_prod", value=False)
            df_show = filtrar_top20(df_if_producto) if solo_top_if_prod else df_if_producto
            pareto_chart(df_show, 'Producto', '❌ No In Full – por Producto', '#3498db')
            with st.expander("📋 Tabla: No In Full por Producto"):
                st.dataframe(df_show, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error al calcular OTIF: {e}")
