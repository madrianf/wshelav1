import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns   
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

import io
from utils.email_sender import send_email_with_attachment
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

conn = st.connection("sqlserver", type="sql")
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

# custom styles
st.markdown("""
<style>
.color1 {color: #060606;}
.color2 {color: #0c2836;}
.color3 {color: #185675;}
.color4 {color: #2689bd;}
.color5 {color: #2bb9c8;}


h1 {font-size:24px !important;}
h2 {font-size:20px !important;}
h3 {font-size:18px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("# Informe Pedidos en Sistema")
st.markdown("---")

# Pre-procesamiento global
df_pedidos['DocDate_DT'] = pd.to_datetime(df_pedidos['DocDate'], errors='coerce')
df_pedidos['Anio'] = df_pedidos['DocDate_DT'].dt.year

# --- FILTRO POR AÑO (PRINCIPAL) ---
current_year = datetime.now().year
years_options = sorted(df_pedidos['Anio'].dropna().unique().astype(int).tolist())
# Aseguramos que el rango sea al menos desde 2022 hasta el año actual
years_range = list(range(2022, current_year + 1))
default_years = [y for y in years_range if y in years_options]

selected_years = st.multiselect(
    "Seleccione el/los años a visualizar:",
    options=years_options,
    default=default_years if default_years else years_options[:1],
    help="Este filtro afecta a todos los datos mostrados en el informe."
)

# Aplicar filtro de año principal
df_pedidos = df_pedidos[df_pedidos['Anio'].isin(selected_years)]

df_filtered = df_pedidos.copy()

# Pre-process for ranges y montos
df_filtered['LineTotal_Num'] = pd.to_numeric(df_filtered['LineTotal'], errors='coerce').fillna(0)
df_filtered['Quantity_Num'] = pd.to_numeric(df_filtered['Quantity'], errors='coerce').fillna(0)

@st.dialog("Exportar a Excel")
def show_export_modal(df):
    st.write("Seleccione el destino del archivo Excel generado.")
    email_dest = st.text_input("✉️ Enviar a email (opcional):", placeholder="ejemplo@empresa.com")
    
    c1, c2 = st.columns(2)
    
    if c1.button("🚀 Crear Excel", use_container_width=True):
        if df.empty:
            st.warning("No hay datos cargados para exportar.")
        else:
            # Generación del archivo (lógica similar a inventario.py)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Usamos una copia limpia para exportar
                df_to_export = df.copy()
                if 'DocDate_DT' in df_to_export.columns: 
                    df_to_export = df_to_export.drop(columns=['DocDate_DT'])
                    
                df_to_export.to_excel(writer, index=False, sheet_name='Pedidos_En_Sistema')
            
            excel_data = output.getvalue()
            
            if email_dest.strip():
                # Enviar por correo
                with st.spinner("Enviando correo..."):
                    exito, mensaje = send_email_with_attachment(
                        destinatario=email_dest.strip(),
                        subject=f"Exportación de Pedidos - {datetime.now().strftime('%d/%m/%Y')}",
                        body="Cordial saludo,\n\nSe adjunta el reporte de pedidos exportado desde el sistema.\n\nAtentamente,\nControl Gestión Ventas",
                        attachment_data=excel_data,
                        filename=f"Pedidos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                    )
                if exito:
                    st.success("✅ Correo enviado correctamente.")
                else:
                    st.error(f"❌ {mensaje}")
            else:
                # Descarga directa
                st.download_button(
                    label="💾 Descargar ahora",
                    data=excel_data,
                    file_name=f"Pedidos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.info("Haz clic en 'Descargar ahora' para guardar el archivo.")
    
    if c2.button("🚫 Salir", use_container_width=True):
        st.rerun()

with st.expander("Filtros de Pedidos", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_numpedido = st.text_input("N° Pedido")
        f_slpcode = st.text_input("Cod Vendedor(a)")
        f_itemcode = st.text_input("Código Artículo")
    with col2:
        f_cardcode = st.text_input("CardCode")
        f_slpname = st.text_input("Nombre Vendedor(a)")
        f_itemname = st.text_input("Nombre Artículo")
    with col3:
        f_cardname = st.markdown(" ") # Espaciador
        f_cardname = st.text_input("CardName")
        f_linestatus = st.selectbox("Estado Línea", ["Todos", "O", "C"], index=0)

    with col4:
        # Date range
        min_date = df_filtered['DocDate_DT'].min()
        max_date = df_filtered['DocDate_DT'].max()
        if pd.isna(min_date) or pd.isna(max_date):
            min_date, max_date = datetime.today().date() - timedelta(days=30), datetime.today().date()
        else:
            min_date, max_date = min_date.date(), max_date.date()
        date_filter = st.date_input("Rango Fecha Pedido", value=[min_date, max_date])

        # Estilo para el botón de exportación en esta columna (Columna 4)
        st.markdown("""
            <style>
            div[data-testid="column"]:nth-child(4) button {
                background-color: #d4edda !important;
                color: #155724 !important;
                border: 1px solid #c3e6cb !important;
                margin-top: 28px !important;
            }
            div[data-testid="column"]:nth-child(4) button:hover {
                background-color: #c3e6cb !important;
                color: #155724 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Botón de exportación (Vuelve a Columna 4)
        if st.button("📥 Exportar a Excel", type="tertiary", use_container_width=True):
            show_export_modal(df_filtered)

# Apply text filters
if f_numpedido: df_filtered = df_filtered[df_filtered['NumPedido'].astype(str).str.contains(f_numpedido, case=False, na=False)]
if f_cardcode: df_filtered = df_filtered[df_filtered['CardCode'].astype(str).str.contains(f_cardcode, case=False, na=False)]
if f_cardname: df_filtered = df_filtered[df_filtered['CardName'].astype(str).str.contains(f_cardname, case=False, na=False)]
if f_slpcode: df_filtered = df_filtered[df_filtered['SlpCode'].astype(str).str.contains(f_slpcode, case=False, na=False)]
if f_slpname: df_filtered = df_filtered[df_filtered['SlpName'].astype(str).str.contains(f_slpname, case=False, na=False)]
if f_itemcode: df_filtered = df_filtered[df_filtered['ItemCode'].astype(str).str.contains(f_itemcode, case=False, na=False)]
if f_itemname: df_filtered = df_filtered[df_filtered['ItemName'].astype(str).str.contains(f_itemname, case=False, na=False)]
if f_linestatus != "Todos": df_filtered = df_filtered[df_filtered['LineStatus'] == f_linestatus]

# Apply range filters
if len(date_filter) == 2:
    df_filtered = df_filtered[(df_filtered['DocDate_DT'].dt.date >= date_filter[0]) & (df_filtered['DocDate_DT'].dt.date <= date_filter[1])]

# Drop temporary columns before rendering, and hide DocEntry/DocStatus
_cols_excluir = ['DocDate_DT', 'LineTotal_Num', 'Quantity_Num', 'DocEntry', 'DocStatus']
df_filtered_view = df_filtered.drop(columns=_cols_excluir, errors='ignore')

# Visualización del dataframe filtrado
st.dataframe(df_filtered_view, use_container_width=True, hide_index=True)

# --- RESUMEN DE TOTALES FILTRADOS ---
# Realizamos los cálculos basados en el DataFrame que ya pasó por todos los filtros (df_filtered)
# Para métricas a nivel de pedido, eliminamos duplicados por DocEntry
df_pedidos_unicos = df_filtered.drop_duplicates("DocEntry")

cant_pedidos = df_pedidos_unicos['NumPedido'].nunique()
cant_clientes = df_pedidos_unicos['CardCode'].nunique()
cant_vendedores = df_pedidos_unicos['SlpCode'].nunique()

val_total = df_filtered['LineTotal_Num'].sum()

st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 0.95rem !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
}
div[data-testid="stMetric"] {
    border: 1px solid #ccc;
    padding: 10px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

cols = st.columns(4)
cols[0].metric("Pedidos", f"{cant_pedidos}")
cols[1].metric("Clientes", f"{cant_clientes}")
cols[2].metric("Vendedores", f"{cant_vendedores}")
cols[3].metric("Total Pedidos", f"${val_total:,.0f}")

# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN: Consultas en Lenguaje Natural con IA
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("# 🤖 Consultas con IA")
st.write("Haz preguntas sobre los pedidos en lenguaje natural. Ejemplo: *¿Cuánto vendió Oscar Hernandez en marzo?*")
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
    
    system_prompt = f"""Eres un asistente experto en análisis de datos con pandas. 
El usuario te hará preguntas sobre un dataframe de pedidos de venta.
Tu trabajo es generar CÓDIGO PYTHON usando pandas para responder la pregunta.

REGLAS:
- El dataframe ya está cargado en la variable 'df'.
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
    
    local_vars = {'df': df.copy(), 'pd': pd, 'np': np}
    try:
        exec(code, {"__builtins__": {}}, local_vars)
        resultado = local_vars.get('resultado', '(Sin variable resultado)')
        return resultado, None
    except Exception as e:
        return None, f"❌ Error al ejecutar: {str(e)}"


# Inicializar historial de chat en session_state
if 'chat_history_pedidos' not in st.session_state:
    st.session_state.chat_history_pedidos = []

# Mostrar historial de chat
for msg in st.session_state.chat_history_pedidos:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # Ocultamos el código generado en el historial
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
user_question = st.chat_input("Pregunta sobre los pedidos... Ej: ¿Top 5 clientes por monto?")

if user_question:
    st.session_state.chat_history_pedidos.append({"role": "user", "content": user_question})
    
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando tu pregunta..."):
            try:
                # Usamos df_filtered para que la IA herede los filtros actuales de la UI
                code = ask_dataframe(user_question, df_filtered)
                
                # Ocultamos el código generado en la respuesta actual
                # with st.expander("📝 Código generado", expanded=False):
                #     st.code(code, language="python")
                
                resultado, error = execute_safe(code, df_filtered)
                
                if error:
                    st.error(error)
                    st.session_state.chat_history_pedidos.append({
                        "role": "assistant",
                        "code": code,
                        "error": error
                    })
                else:
                    if isinstance(resultado, pd.DataFrame):
                        st.dataframe(resultado, use_container_width=True, hide_index=True)
                    else:
                        st.markdown(f"**Resultado:** {resultado}")
                    
                    st.session_state.chat_history_pedidos.append({
                        "role": "assistant",
                        "code": code,
                        "result": resultado
                    })
            except Exception as e:
                st.error(f"❌ Error al comunicarse con OpenAI: {str(e)}")
                st.session_state.chat_history_pedidos.append({
                    "role": "assistant",
                    "error": f"Error de OpenAI: {str(e)}"
                })

