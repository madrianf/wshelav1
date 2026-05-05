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

# Filtrar solo pedidos abiertos (pendientes de facturar)
df_pedidos = df_pedidos[df_pedidos['DocStatus'] == 'O']

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
    min-height: 125px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.stMetric .stMetricValue { font-size: 1rem !important; }
.stMetric .stMetricLabel { font-size: 0.85rem !important; }

h1 {font-size:24px !important;}
h2 {font-size:20px !important;}
h3 {font-size:18px !important;}
</style>
""", unsafe_allow_html=True)

# Contenedor para el botón de exportar (se renderizará aquí pero se llenará al final)
export_container = st.container()

with export_container:
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.markdown("# Pedidos por Facturar")
        st.write("Listado de pedidos abiertos (pendientes de facturación)")
    # El botón se colocará en col_t2 al final del script

st.markdown("---")

df_filtered = df_pedidos.copy()

# Activar modal si se presionó el botón
# Nota: Streamlit ejecuta de arriba a abajo, el botón ya se definió arriba.
# Pero necesitamos df_filtered que se calcula aquí.
# Para que funcione bien con el botón superior, moveremos el botón después del filtrado 
# o usaremos session_state. 
# Simplificación: Mover el bloque de título después del filtrado inicial.

# Pre-process for ranges
df_filtered['DocDate_DT'] = pd.to_datetime(df_filtered['DocDate'], errors='coerce')
df_filtered['LineTotal_Num'] = pd.to_numeric(df_filtered['LineTotal'], errors='coerce').fillna(0)

with st.expander("Filtros de Pedidos", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_numpedido = st.text_input("N° Pedido")
        f_itemcode = st.text_input("ItemCode")
    with col2:
        f_cardcode = st.text_input("CardCode")
        f_itemname = st.text_input("ItemName")
    with col3:
        f_cardname = st.text_input("CardName")
        f_slpname = st.text_input("Nombre Vendedor(a)")
    with col4:
        # Date range
        min_date = df_filtered['DocDate_DT'].min()
        max_date = df_filtered['DocDate_DT'].max()
        if pd.isna(min_date) or pd.isna(max_date):
            min_date, max_date = datetime.today().date() - timedelta(days=30), datetime.today().date()
        else:
            min_date, max_date = min_date.date(), max_date.date()
        date_filter = st.date_input("Rango DocDate", value=[min_date, max_date])
        
        # LineTotal range
        min_tot = float(df_filtered['LineTotal_Num'].min())
        max_tot = float(df_filtered['LineTotal_Num'].max())
        if min_tot == max_tot: max_tot += 1.0 # prevent slider crash
        monto_filter = st.slider("Rango Total Venta", min_value=min_tot, max_value=max_tot, value=(min_tot, max_tot))

# Apply text filters
if f_numpedido: df_filtered = df_filtered[df_filtered['NumPedido'].astype(str).str.contains(f_numpedido, case=False, na=False)]
if f_itemcode: df_filtered = df_filtered[df_filtered['ItemCode'].astype(str).str.contains(f_itemcode, case=False, na=False)]
if f_cardcode: df_filtered = df_filtered[df_filtered['CardCode'].astype(str).str.contains(f_cardcode, case=False, na=False)]
if f_itemname: df_filtered = df_filtered[df_filtered['ItemName'].astype(str).str.contains(f_itemname, case=False, na=False)]
if f_cardname: df_filtered = df_filtered[df_filtered['CardName'].astype(str).str.contains(f_cardname, case=False, na=False)]
if f_slpname: df_filtered = df_filtered[df_filtered['SlpName'].astype(str).str.contains(f_slpname, case=False, na=False)]

# Apply range filters
if len(date_filter) == 2:
    df_filtered = df_filtered[(df_filtered['DocDate_DT'].dt.date >= date_filter[0]) & (df_filtered['DocDate_DT'].dt.date <= date_filter[1])]
    
df_filtered = df_filtered[(df_filtered['LineTotal_Num'] >= monto_filter[0]) & (df_filtered['LineTotal_Num'] <= monto_filter[1])]

# Cálculos de los KPIs basados en el filtro actual
df_filtered_unicos = df_filtered.drop_duplicates("DocEntry")

total_pedidos = df_filtered_unicos['NumPedido'].nunique() if not df_filtered_unicos.empty else 0
total_clientes = df_filtered_unicos['CardCode'].nunique() if not df_filtered_unicos.empty else 0
total_facturar = df_filtered['LineTotal_Num'].sum()

# Calculo Pedidos Vencidos (DocDueDate <= hoy) sobre el filtro actual
# Usamos una copia para no alterar el dataframe de visualización
df_venc_calc = df_filtered_unicos.copy()
df_venc_calc['DocDueDate_DT'] = pd.to_datetime(df_venc_calc['DocDueDate'], errors='coerce')
hoy = pd.Timestamp.today().normalize()
pedidos_vencidos_df = df_venc_calc[df_venc_calc['DocDueDate_DT'] <= hoy]
cant_vencidos = len(pedidos_vencidos_df) if not pedidos_vencidos_df.empty else 0

# Drop temporary columns before rendering
_cols_excluir = ['DocDate_DT', 'LineTotal_Num', 'DocEntry', 'DocStatus']
df_render = df_filtered.drop(columns=_cols_excluir, errors='ignore')

# Lógica del botón de exportación (Patrón ordenes.py)
with export_container:
    with col_t2:
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                # Limpieza para exportación
                df_exp = df_filtered.copy()
                cols_drop = ['DocDate_DT', 'LineTotal_Num', 'DocEntry', 'DocStatus']
                df_exp = df_exp.drop(columns=[c for c in cols_drop if c in df_exp.columns], errors='ignore')
                df_exp.to_excel(writer, index=False, sheet_name='Pedidos_Pendientes')
            
            st.download_button(
                label="📥 Exportar Excel",
                data=buf.getvalue(),
                file_name=f"Pedidos_Por_Facturar_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_export_direct"
            )
        except Exception as e:
            st.error(f"Error al generar Excel: {e}")

# Mostrar grid
st.dataframe(df_render, use_container_width=True, hide_index=True)

st.markdown("### Resumen de Selección")
col1, col2, col3, col4 = st.columns(4)

col1.metric("N° Pedidos Filtrados", f"{total_pedidos}")
col2.metric("Total por Facturar ($)", f"${total_facturar:,.0f}")
col3.metric("Pedidos Vencidos (Entrega)", f"{cant_vencidos}", 
            delta=f"{cant_vencidos} Pedidos" if cant_vencidos > 0 else "0 Pedidos", 
            delta_color="inverse" if cant_vencidos > 0 else "off")
col4.metric("N° Clientes Filtrados", f"{total_clientes}")

st.markdown("<br>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN: Consultas en Lenguaje Natural con IA
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("# 🤖 Consultas con IA")
st.write("Haz preguntas sobre los pedidos por facturar en lenguaje natural. Ejemplo: *¿Cuántos kilos faltan por facturar este mes?*")
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
El usuario te hará preguntas sobre un dataframe de pedidos que están Pendientes de Facturar.
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


# Inicializar historial de chat en session_state independiente
if 'chat_history_pendientes' not in st.session_state:
    st.session_state.chat_history_pendientes = []

# Mostrar historial de chat
for msg in st.session_state.chat_history_pendientes:
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
user_question = st.chat_input("Pregunta sobre pedidos por facturar... Ej: ¿Qué clientes tienen más kilos pendientes?")

if user_question:
    st.session_state.chat_history_pendientes.append({"role": "user", "content": user_question})
    
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando tus pedidos por facturar..."):
            try:
                # Usamos df_filtered para que la IA herede los filtros actuales de la UI
                code = ask_dataframe(user_question, df_filtered)
                
                # Ocultamos el código generado en la respuesta actual
                # with st.expander("📝 Código generado", expanded=False):
                #     st.code(code, language="python")
                
                resultado, error = execute_safe(code, df_filtered)
                
                if error:
                    st.error(error)
                    st.session_state.chat_history_pendientes.append({
                        "role": "assistant",
                        "code": code,
                        "error": error
                    })
                else:
                    if isinstance(resultado, pd.DataFrame):
                        st.dataframe(resultado, use_container_width=True, hide_index=True)
                    else:
                        st.markdown(f"**Resultado:** {resultado}")
                    
                    st.session_state.chat_history_pendientes.append({
                        "role": "assistant",
                        "code": code,
                        "result": resultado
                    })
            except Exception as e:
                st.error(f"❌ Error al comunicarse con OpenAI: {str(e)}")
                st.session_state.chat_history_pendientes.append({
                    "role": "assistant",
                    "error": f"Error de OpenAI: {str(e)}"
                })
