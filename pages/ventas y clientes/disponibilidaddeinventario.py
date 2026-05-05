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
df_proyeccion_of = conn.query("""
SELECT [ItemCode]
      ,[ItemName]
      ,[UM]
      ,[Stock Kg]
      ,[Stock Comprometido Kg]
      ,[Stock Compras Kg]
      ,[Stock Disponible Kg]
      ,[Stock Envasado (UN)]
      ,[Costo UN]
      ,[Costo x Kg]
      ,[Costo Total Envasado (UN)]
      ,[Costo Total Kilos]
  FROM [SBO_HELA].[dbo].[Z_VIEW_STOCK_DISPONIBLE_PT]
""")

# Pre-procesamiento
# (Se eliminaron conversiones de Dias Venc/Meses Venc ya que no vienen en la nueva query)






# (Se eliminaron datos de prueba y categorías obsoletas)

# configure page and sidebar before rendering any widgets
st.set_page_config(page_title="Análisis de Inventario", layout="wide")

# custom styles: card borders and smaller fonts for metrics and titles
st.markdown("""
<style>

/* Paleta de colores */
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
.stMetric .stMetricValue {
    font-size: 1rem !important;
}
.stMetric .stMetricLabel {
    font-size: 0.85rem !important;
}

h1 {font-size:24px !important;}
h2 {font-size:20px !important;}
h3 {font-size:18px !important;}

/* Estilos de botones para el sidebar */
[data-testid="stSidebar"] div.stButton > button {
    background-color: #060606 !importat;
    color: white !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #1c1b31 !important; 
}
</style>
""", unsafe_allow_html=True)

st.markdown("# Informe Disponibilidad de Inventario")
st.write("Stock disponible de productos terminados")
st.markdown("---")

df_proyeccion_of_filtered = df_proyeccion_of.copy()

with st.expander("Filtros por Columna", expanded=True):
    filtros_permitidos = ['ItemCode', 'ItemName']
    cols = st.columns(len(filtros_permitidos))
    for i, col_name in enumerate(filtros_permitidos):
        if col_name in df_proyeccion_of.columns:
            with cols[i]:
                search_val = st.text_input(col_name, key=f"search_{col_name}", placeholder="...")
                if search_val:
                    df_proyeccion_of_filtered = df_proyeccion_of_filtered[
                        df_proyeccion_of_filtered[col_name].astype(str).str.contains(search_val, case=False, na=False)
                    ]

# Renderizado del DataFrame
st.dataframe(df_proyeccion_of_filtered, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN: Consultas en Lenguaje Natural con IA
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("# 🤖 Consultas con IA")
st.write("Haz preguntas sobre el inventario en lenguaje natural. Ejemplo: *¿Cuántos kilos de materia prima hay?*")
st.markdown("---")

# Inicializar cliente OpenAI con Langchain
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=10000,
    api_key=st.secrets["openai"]["api_key"]
)

# Preparar contexto del dataframe para el LLM
def get_df_context(df):
    """Genera un resumen del dataframe para enviar al LLM."""
    info_lines = []
    info_lines.append(f"El dataframe se llama 'df' y tiene {len(df)} filas y {len(df.columns)} columnas.")
    info_lines.append(f"Columnas: {list(df.columns)}")
    info_lines.append(f"Tipos de datos:\n{df.dtypes.to_string()}")
    info_lines.append(f"Valores únicos por columna categórica:")
    for col in df.select_dtypes(include=['object']).columns:
        unicos = df[col].dropna().unique()
        if len(unicos) <= 30:
            info_lines.append(f"  - {col}: {list(unicos)}")
        else:
            info_lines.append(f"  - {col}: {list(unicos[:15])} ... ({len(unicos)} valores únicos)")
    info_lines.append(f"\nPrimeras 3 filas de ejemplo:\n{df.head(3).to_string()}")
    info_lines.append(f"\nEstadísticas numéricas:\n{df.describe().to_string()}")
    return "\n".join(info_lines)


def ask_dataframe(question: str, df: pd.DataFrame) -> dict:
    """Envía una pregunta en lenguaje natural y obtiene código pandas + resultado."""
    df_context = get_df_context(df)
    
    system_prompt = f"""Eres un asistente experto en análisis de datos con pandas para Antigravity. 
El usuario te hará preguntas sobre el inventario de Producto Terminado (PT).
Tu trabajo es generar EXCLUSIVAMENTE CÓDIGO PYTHON usando pandas para responder.

REGLAS DE NEGOCIO (SKILL INVENTARIO.md):
- Este reporte se rige por las reglas del archivo INVENTARIO.md.
- La columna 'Kilos Disponibles' es el saldo neto real disponible para ventas.
- 'Stock_Kilos' representa las unidades físicas en stock.
- Para valorizaciones monetarias, utiliza 'Costo Total' o 'Costo por Kilo'.

REGLAS TÉCNICAS:
- El dataframe ya está cargado en la variable 'df'.
- Usa SOLO pandas, numpy y operaciones básicas de Python.
- NO uses import, exec, eval, open, os, sys, subprocess ni nada peligroso.
- El resultado final DEBE guardarse en una variable llamada 'resultado'.
- Responde en español.
- NO incluyas explicaciones, comentarios ni bloques de markdown (como ```python). Solo devuelve el código puro.

INFORMACIÓN DEL DATAFRAME:
{df_context}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    response = llm.invoke(messages)
    
    code = response.content.strip()
    # Limpiar posibles bloques markdown
    if code.startswith("```"):
        code = code.split("\n", 1)[1]  # quitar primera línea ```python
        code = code.rsplit("```", 1)[0]  # quitar último ```
    
    return code


def execute_safe(code: str, df: pd.DataFrame):
    """Ejecuta código pandas de forma controlada."""
    # Palabras prohibidas por seguridad
    forbidden = ['import ', 'exec(', 'eval(', 'open(', '__', 'os.', 'sys.', 'subprocess', 'shutil', 'globals', 'locals']
    for word in forbidden:
        if word in code:
            return None, f"⚠️ Código rechazado por seguridad: contiene '{word}'"
    
    local_vars = {'df': df.copy(), 'pd': pd, 'np': np}
    try:
        exec(code, {"__builtins__": {}}, local_vars)
        resultado = local_vars.get('resultado', '(Sin variable resultado)')
        return resultado, None
    except Exception as e:
        return None, f"❌ Error al ejecutar: {str(e)}"


# Inicializar historial de chat en session_state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Mostrar historial de chat
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # Ocultamos el código generado por defecto
            # if "code" in msg:
            #     with st.expander("📝 Código generado", expanded=False):
            #         st.code(msg["code"], language="python")
            if "error" in msg and msg["error"]:
                st.error(msg["error"])
            elif "result" in msg:
                result = msg["result"]
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"**Resultado:** {result}")

# Input de la pregunta
user_question = st.chat_input("Preguntá sobre el inventario... Ej: ¿Cuántos artículos vencidos hay?")

if user_question:
    # Agregar pregunta del usuario al historial
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando tu pregunta..."):
            try:
                code = ask_dataframe(user_question, df_proyeccion_of_filtered)
                
                # Ocultamos el código generado en la respuesta actual
                # with st.expander("📝 Código generado", expanded=False):
                #     st.code(code, language="python")
                
                resultado, error = execute_safe(code, df_proyeccion_of_filtered)
                
                if error:
                    st.error(error)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "code": code,
                        "error": error
                    })
                else:
                    if isinstance(resultado, pd.DataFrame):
                        st.dataframe(resultado, use_container_width=True, hide_index=True)
                    else:
                        st.markdown(f"**Resultado:** {resultado}")
                    
                    # Serializar resultado para historial
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "code": code,
                        "result": resultado
                    })
            except Exception as e:
                st.error(f"❌ Error al comunicarse con OpenAI: {str(e)}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "error": f"Error de OpenAI: {str(e)}"
                })
