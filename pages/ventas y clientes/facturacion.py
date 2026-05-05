import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns   
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

conn = st.connection("sqlserver", type="sql")
df_ventasrealizadas = conn.query("""
SELECT [CardCode]
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
  FROM [SBO_HELA].[dbo].[Z_VIEW_VENTAS_HISTORICO]
""")

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

st.markdown("# Ventas Realizadas")
st.write("Histórico de facturación")
st.markdown("---")

# Pre-procesamiento de fechas y campos derivados
df_ventasrealizadas['DocDate_DT'] = pd.to_datetime(df_ventasrealizadas['DocDate'], errors='coerce')
df_ventasrealizadas['año_int'] = df_ventasrealizadas['año']
df_ventasrealizadas['mes_str'] = df_ventasrealizadas['mes']

# Calcular Margen (Utilizando LineTotal y CostoTotal)
df_ventasrealizadas['LineTotal_Num'] = pd.to_numeric(df_ventasrealizadas['LineTotal'], errors='coerce').fillna(0)
df_ventasrealizadas['CostoTotal_Num'] = pd.to_numeric(df_ventasrealizadas['CostoTotal'], errors='coerce').fillna(0)
df_ventasrealizadas['Quantity_Num'] = pd.to_numeric(df_ventasrealizadas['Quantity'], errors='coerce').fillna(0)

# El beneficio (Margen $) es LineTotal - CostoTotal
# El margen % es (Margen $ / LineTotal) * 100
df_ventasrealizadas['Margen $'] = df_ventasrealizadas['LineTotal_Num'] - df_ventasrealizadas['CostoTotal_Num']
df_ventasrealizadas['Margen %'] = (df_ventasrealizadas['Margen $'] / df_ventasrealizadas['LineTotal_Num'].replace(0, np.nan)) * 100
df_ventasrealizadas['Margen %'] = df_ventasrealizadas['Margen %'].fillna(0)

# --- FILTRO POR AÑO (PRINCIPAL) ---
current_year = datetime.now().year
years_options = sorted(df_ventasrealizadas['año'].dropna().unique().astype(int).tolist())
years_range = list(range(2022, current_year + 1))
default_years = [y for y in years_range if y in years_options]

selected_years = st.multiselect(
    "Seleccione el/los años de facturación:",
    options=years_options,
    default=default_years if default_years else years_options[-1:],
    help="Este filtro afecta a todos los datos mostrados en el reporte."
)

# Aplicar filtro de año principal
df_ventasrealizadas = df_ventasrealizadas[df_ventasrealizadas['año_int'].isin(selected_years)]
df_filtered = df_ventasrealizadas.copy()

with st.expander("🔍 Explorar y Filtrar Ventas", expanded=True):
    # ─── FILTROS PRINCIPALES ──────────────────────────────────────────────────
    # Rango de fechas basado en los datos cargados
    if not df_filtered.empty:
        min_date = df_filtered['DocDate_DT'].min().date()
        max_date = df_filtered['DocDate_DT'].max().date()
        date_filter = st.date_input("Rango de Fechas (Facturación)", value=[min_date, max_date])
    else:
        date_filter = []

    # Aplicar filtros principales
    if len(date_filter) == 2:
        df_filtered = df_filtered[(df_filtered['DocDate_DT'].dt.date >= date_filter[0]) & (df_filtered['DocDate_DT'].dt.date <= date_filter[1])]

    st.markdown("---")
    st.markdown("### Buscadores por Texto")
    
    # Excluimos técnicos, numéricos y los que ya tienen controles específicos
    cols_to_exclude = [
        "LineTotal_Num", "CostoTotal_Num", "Quantity_Num", "Margen $", "DocDate_DT", "año_int", "Margen %", 
        "mes_str", "año", "mes", "DocDate", "DocStatus", "Quantity", "Margen", "stockprice", "UnitMsr", "Notes",
        "CostoTotal", "Price", "LineTotal"
    ]
    selectable_cols = [c for c in df_ventasrealizadas.columns if c not in cols_to_exclude]
    
    columns_per_row = 4
    for i in range(0, len(selectable_cols), columns_per_row):
        row_cols = st.columns(columns_per_row)
        for j, col_name in enumerate(selectable_cols[i:i + columns_per_row]):
            with row_cols[j]:
                search_val = st.text_input(f"Filtrar {col_name}", key=f"search_{col_name}", placeholder="...")
                if search_val:
                    df_filtered = df_filtered[
                        df_filtered[col_name].astype(str).str.contains(search_val, case=False, na=False)
                    ]

st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# ─── RESUMEN DE SELECCIÓN (KPIs) ───────────────────────────────────────────────
df_filt_unicos = df_filtered.drop_duplicates("DocNum")

cant_facturas = df_filt_unicos['DocNum'].nunique() if not df_filt_unicos.empty else 0
cant_clientes = df_filt_unicos['CardCode'].nunique() if not df_filt_unicos.empty else 0
cant_vendedores = df_filt_unicos['SlpName'].nunique() if not df_filt_unicos.empty else 0
cant_items = df_filtered['ItemCode'].nunique() if not df_filtered.empty else 0

val_total = df_filtered['LineTotal_Num'].sum()

st.markdown("### Resúmen")

# Fila 1: Conteos (4 columnas)
c_row1_1, c_row1_2, c_row1_3, c_row1_4 = st.columns(4)
c_row1_1.metric("N° Facturas", f"{cant_facturas:,.0f}")
c_row1_2.metric("N° Clientes", f"{cant_clientes:,.0f}")
c_row1_3.metric("N° Vendedores", f"{cant_vendedores:,.0f}")
c_row1_4.metric("N° Items Únicos", f"{cant_items:,.0f}")

# Fila 2: Totales (1 columna)
st.metric("Total Ventas", f"${val_total:,.0f}")


st.markdown("<br>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN: Consultas en Lenguaje Natural con IA
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("# 🤖 Consultas con IA")
st.write("Haz preguntas sobre las ventas realizadas en lenguaje natural. Ejemplo: *¿Cuánto se facturó en total el año pasado?*")
st.markdown("---")

# Inicializar cliente OpenAI con Langchain desde secrets
try:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=1024,
        api_key=st.secrets["openai"]["api_key"]
    )
except Exception as e:
    st.error("Error al configurar OpenAI. Verifique secrets.toml.")
    st.stop()

# Preparar contexto del dataframe para el LLM
def get_df_context(df_filt_unicos):
    """Genera un resumen del dataframe para enviar al LLM."""
    info_lines = []
    info_lines.append(f"El dataframe se llama 'df_filt_unicos' y tiene {len(df_filt_unicos)} filas y {len(df_filt_unicos.columns)} columnas.")
    info_lines.append(f"Columnas: {list(df_filt_unicos.columns)}")
    info_lines.append(f"Tipos de datos:\n{df_filt_unicos.dtypes.to_string()}")
    info_lines.append(f"Valores únicos por columna categórica:")
    for col in df_filt_unicos.select_dtypes(include=['object']).columns:
        unicos = df_filt_unicos[col].dropna().unique()
        if len(unicos) <= 30:
            info_lines.append(f"  - {col}: {list(unicos)}")
        else:
            info_lines.append(f"  - {col}: {list(unicos[:15])} ... ({len(unicos)} valores únicos)")
    info_lines.append(f"\nPrimeras 3 filas de ejemplo:\n{df_filt_unicos.head(3).to_string()}")
    info_lines.append(f"\nEstadísticas numéricas:\n{df_filt_unicos.describe().to_string()}")
    return "\n".join(info_lines)


def ask_dataframe(question: str, df_filt_unicos: pd.DataFrame) -> dict:
    """Envía una pregunta en lenguaje natural y obtiene código pandas + resultado."""
    df_context = get_df_context(df_filt_unicos)
    
    system_prompt = f"""Eres un asistente experto en análisis de datos con pandas. 
El usuario te hará preguntas sobre un dataframe que contiene el histórico de VENTAS REALIZADAS (Facturación).
Tu trabajo es generar CÓDIGO PYTHON usando pandas para responder la pregunta.

REGLAS:
- El dataframe ya está cargado en la variable 'df_filt_unicos'.
- Usa SOLO pandas, numpy y operaciones básicas de Python.
- NO uses import, exec, eval, open, os, sys, subprocess ni nada peligroso.
- El resultado final DEBE guardarse en una variable llamada 'resultado'.
- Si la respuesta es un número, 'resultado' debe ser ese número.
- Si la respuesta es una tabla, 'resultado' debe ser un DataFrame.
- Si la respuesta es texto, 'resultado' debe ser un string.
- Responde en español.
- NO incluyas explicaciones, SOLO el código Python.
- NO uses bloques de markdown como ```python, devuelve código puro.

INFORMACIÓN DEL DATAFRAME:
{df_context}    
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    response = llm.invoke(messages)
    
    code = response.content.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[1]
        code = code.rsplit("```", 1)[0]
    
    return code


def execute_safe(code: str, df: pd.DataFrame):
    """Ejecuta código pandas de forma controlada."""
    forbidden = ['import ', 'exec(', 'eval(', 'open(', '__', 'os.', 'sys.', 'subprocess', 'shutil', 'globals', 'locals']
    for word in forbidden:
        if word in code:
            return None, f"⚠️ Código rechazado por seguridad: contiene '{word}'"
    
    local_vars = {'df_filt_unicos': df.copy(), 'pd': pd, 'np': np}
    try:
        exec(code, {"__builtins__": {}}, local_vars)
        resultado = local_vars.get('resultado', '(Sin variable resultado)')
        return resultado, None
    except Exception as e:
        return None, f"❌ Error al ejecutar: {str(e)}"


# Inicializar historial de chat en session_state independiente para facturación
if 'chat_history_facturacion' not in st.session_state:
    st.session_state.chat_history_facturacion = []

# Mostrar historial de chat
for msg in st.session_state.chat_history_facturacion:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            if "error" in msg and msg["error"]:
                st.error(msg["error"])
            elif "result" in msg:
                result = msg["result"]
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"**Resultado:** {result}")

# Input de la pregunta
user_question = st.chat_input("Pregunta sobre las ventas realizadas... Ej: ¿Cuál fue el margen promedio este mes?")

if user_question:
    st.session_state.chat_history_facturacion.append({"role": "user", "content": user_question})
    
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando el historial de facturación..."):
            try:
                # Usamos df_filtered para que la IA herede los filtros actuales de la UI
                code = ask_dataframe(user_question, df_filtered)
                
                resultado, error = execute_safe(code, df_filtered)
                
                if error:
                    st.error(error)
                    st.session_state.chat_history_facturacion.append({
                        "role": "assistant",
                        "code": code,
                        "error": error
                    })
                else:
                    if isinstance(resultado, pd.DataFrame):
                        st.dataframe(resultado, use_container_width=True, hide_index=True)
                    else:
                        st.markdown(f"**Resultado:** {resultado}")
                    
                    st.session_state.chat_history_facturacion.append({
                        "role": "assistant",
                        "code": code,
                        "result": resultado
                    })
            except Exception as e:
                st.error(f"❌ Error al comunicarse con OpenAI: {str(e)}")
                st.session_state.chat_history_facturacion.append({
                    "role": "assistant",
                    "error": f"Error de OpenAI: {str(e)}"
                })
