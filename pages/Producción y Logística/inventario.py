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

DECLARE @YAPO VARCHAR(50) = CONVERT(VARCHAR(50), GETDATE(),101);
DECLARE @hoy DATETIME = SUBSTRING(@YAPO,7,4) + '-' + SUBSTRING(@YAPO,4,2) + '-' + SUBSTRING(@YAPO,1,2) + ' 00:00:00.000';

     SELECT OWHS.WhsCode, OWHS.WhsName, OITM.ItemCode, OITM.ItemName, 
     CASE WHEN OITM.U_ARTI_GRUPO='1' THEN 'PRODUCTO TERMINADO' WHEN OITM.U_ARTI_GRUPO='2' THEN 'MATERIA PRIMA' WHEN OITM.U_ARTI_GRUPO='5' THEN 'INSUMO EMBALAJE' WHEN OITM.U_ARTI_GRUPO='3' THEN 'REVENTA' WHEN OITM.U_ARTI_GRUPO='4' THEN 'SEMI ELABORADO' END AS Grupo , 
     OITB.ItmsGrpNam AS 'Categoria',
     ISNULL(OBIN.BinCode, '') AS BinCode, ISNULL(OBTN.DistNumber, '') AS Lote, 
        CASE WHEN ISNULL(OBBQ.OnHandQty, 0) = 0 THEN OITW.OnHand ELSE OBBQ.OnHandQty END as 'Stock_Unidades',
        CASE WHEN ISNULL(OBBQ.OnHandQty, 0) = 0 THEN OITW.OnHand * (OITM.U_ARTI_FACTOR_KILO * OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION) 
            ELSE OBBQ.OnHandQty * (OITM.U_ARTI_FACTOR_KILO * OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION) END as 'Stock_ Kilos',
        OBTN.InDate, OBTN.ExpDate, DATEDIFF(day, @hoy, OBTN.ExpDate) as 'Dias Venc', DATEDIFF(month, @hoy, OBTN.ExpDate) as 'Meses Venc',

        CASE WHEN DATEDIFF(month, @hoy, OBTN.ExpDate) < 0 THEN 'VENCIDO' 
             WHEN (DATEDIFF(month, @hoy, OBTN.ExpDate) >= 0 AND DATEDIFF(month, @hoy, OBTN.ExpDate) <= 3 ) THEN 'ATENCIÓN' 
             WHEN DATEDIFF(month, @hoy, OBTN.ExpDate) > 3 THEN 'SALUDABLE' ELSE '' END as 'Status Venc',
        OITM.AvgPrice as 'Costo Unid', (OITM.AvgPrice * CASE WHEN ISNULL(OBBQ.onHandQty, 0) = 0 THEN OITM.OnHand ELSE OBBQ.onHandQty END) as 'Costo Total',
        (OITM.AvgPrice / (ISNULL(OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(OITM.U_ARTI_FACTOR_KILO, 1) )) as 'Costo por Kilo',
        (OITW.IsCommited * (ISNULL(OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(OITM.U_ARTI_FACTOR_KILO, 1))) 'Kilos Comprometidos',
        (OITW.OnOrder * (ISNULL(OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(OITM.U_ARTI_FACTOR_KILO, 1))) 'Kilos Pedidos a Prov',
         (  
            (OITW.OnHand * (OITM.U_ARTI_FACTOR_KILO * OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION)) 
          - (OITW.IsCommited * (ISNULL(OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(OITM.U_ARTI_FACTOR_KILO, 1)))  
          + (OITW.OnOrder * (ISNULL(OITM.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(OITM.U_ARTI_FACTOR_KILO, 1)))
         ) as 'Kilos Disponibles'

     FROM OWHS 
        INNER JOIN OITW ON (OWHS.WhsCode = OITW.WhsCode)
        INNER JOIN OITM ON (OITW.ItemCode = OITM.ItemCode)
        INNER JOIN OITB ON (OITM.ItmsGrpCod = OITB.ItmsGrpCod)
        LEFT JOIN OBBQ ON (OWHS.WhsCode = OBBQ.WhsCode and OITM.ItemCode = OBBQ.ItemCode)
        INNER JOIN OBIN ON (OBBQ.BinAbs = OBIN.AbsEntry)
        INNER JOIN OBTN ON (OBBQ.SnBMDAbs = OBTN.AbsEntry)             
     where ISNUMERIC(OITM.ItemCode) = 0 AND LEFT(OITM.ItemName, 3) <> '*D*' and OITM.OnHand > 0 AND OBBQ.OnHandQty > 0 AND OITM.U_ARTI_GRUPO = '1'
    """)

# Convertir columnas a enteros (manejando posibles nulos con Int64 de pandas)
df_proyeccion_of['Dias Venc'] = df_proyeccion_of['Dias Venc'].astype('Int64')
df_proyeccion_of['Meses Venc'] = df_proyeccion_of['Meses Venc'].astype('Int64')





productos_clasificados = ['Producto en Polvo', 'Producto Liquido', 'Accesorio']
productos_grupo = ['Producto Terminado', 'Materia Prima', 'Reventa','Premezcla', 'Insumo']
productos_alergenos = ['Producto con Alérgenos', 'Producto sin Alérgenos']
productos_unidad = ['Unidad', 'Kilos']
productos_embalaje = ['Caja', 'Bolsa', 'Botella', 'Unidad', 'Pocillo', 'Bidón','Balde','Octobins','Saco','Otro']
productos_categoria = ['Mezcla De Fosfatos', 
                        'Antioxidante',
                        'Sales De Cura Y Nitrificada',
                        'Preservante / Bacteriostático / Fungistático',
                        'Colorantes',
                        'Otros',
                        'Salmuera',
                        'Proteinas Vegetales, Animales Y Fibras',
                        'Empanizador Y Batidos',
                        'Especias',
                        'Vegetal Deshidratado',
                        'Solubles',
                        'Condimento',
                        'Aplicaciones Dulces',
                        'Liofilizado',
                        'Mallas',
                        'Salsas',
                        'Compound',
                        'Sabores',
                        'Extractos De Levadura Y Levadura Nutricional',
                        'Semillas',
                        'Oleorresinas',
                        'Hela Alemania']
np.random.seed(42)
fechas = pd.date_range(start='2024-01-01', end='2025-12-31', freq='D')
productos = ['SALSA ZUCHINNI','LOMITO 20 FRIOSA','COMPOUND LONGANIZA BIELEFELD','PIMIENTA MACHACADA COSTA','ESPINACA PARA GNOQUIS','CONDIMENTO CARNES POLVO','CANELA AZUCARADA']


data = []
for producto in productos:
    categoria = np.random.choice(productos_categoria)
    clasificacion = np.random.choice(productos_clasificados)
    grupo = np.random.choice(productos_grupo)
    alergenos = np.random.choice(productos_alergenos)
    unidad = np.random.choice(productos_unidad)
    embalaje = np.random.choice(productos_embalaje)
    stock = np.random.randint(10, 15000)
    data.append([producto, categoria, clasificacion, grupo, alergenos, unidad, embalaje, stock])

df = pd.DataFrame(data, columns=['Producto', 'Categoría', 'Clasificación', 'Grupo', 'Alergenos', 'Unidad', 'Embalaje', 'Stock'])

df_grupo = df.groupby('Grupo')['Stock'].sum().reset_index()
df_categoria = df.groupby('Categoría')['Stock'].sum().reset_index()
df_clasificacion = df.groupby('Clasificación')['Stock'].sum().reset_index()
df_alergenos = df.groupby('Alergenos')['Stock'].sum().reset_index()
df_embalaje = df.groupby('Embalaje')['Stock'].sum().reset_index()
# ensure columna Unidad existe
assert 'Unidad' in df.columns, f"Columnas disponibles: {df.columns.tolist()}"
df_unidad = df.groupby('Unidad')['Stock'].sum().reset_index()

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

st.markdown("# Informe Inventario")
st.write("Lista de inventario con articulos saldo positivo")
st.markdown("---")

df_proyeccion_of_filtered = df_proyeccion_of.copy()

with st.expander("Tabla de Inventario y Totales", expanded=True):
    with st.expander("Filtros y Exportación", expanded=False):
        filtros_permitidos = ['Grupo', 'Categoria', 'ItemCode', 'ItemName', 'Status Venc']
        cols = st.columns([1, 1, 1, 1, 1, 1.2]) 
        for i, col_name in enumerate(filtros_permitidos):
            if col_name in df_proyeccion_of.columns:
                with cols[i]:
                    search_val = st.text_input(col_name, key=f"search_{col_name}", placeholder="...")
                    if search_val:
                        df_proyeccion_of_filtered = df_proyeccion_of_filtered[
                            df_proyeccion_of_filtered[col_name].astype(str).str.contains(search_val, case=False, na=False)
                        ]

    df_grouped_comprometido = df_proyeccion_of_filtered.groupby(['ItemCode', 'WhsCode'])['Kilos Comprometidos'].first()
    df_grouped_pedidos = df_proyeccion_of_filtered.groupby(['ItemCode', 'WhsCode'])['Kilos Pedidos a Prov'].first()
    
    total_stock_unidades = df_proyeccion_of_filtered['Stock_Unidades'].sum()
    total_stock_kilos = df_proyeccion_of_filtered['Stock_ Kilos'].sum()
    total_comprometido = df_grouped_comprometido.sum() if not df_grouped_comprometido.empty else 0
    total_pedidos = df_grouped_pedidos.sum() if not df_grouped_pedidos.empty else 0
    total_saldo_disponible = total_stock_kilos - total_comprometido + total_pedidos

    with cols[5]:
        import io
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_proyeccion_of_filtered.to_excel(writer, sheet_name='Inventario', index=False)
                totales_df = pd.DataFrame({
                    'Métrica': ['Stock Unidades', 'Stock Kilos', 'Kilos Comprometidos', 'Kilos Pedidos a Prov', 'Kilos Disponibles'],
                    'Valor': [total_stock_unidades, total_stock_kilos, total_comprometido, total_pedidos, total_saldo_disponible]
                })
                totales_df.to_excel(writer, sheet_name='Totales', index=False)
            
            st.download_button(
                label="📥 Exportar a Excel",
                data=buf.getvalue(),
                file_name="Inventario_Exportacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            st.error("⚠️ Falta instalar 'openpyxl'. Por favor, en tu terminal ejecuta: pip install openpyxl")

    def color_status_venc(val):
        if val == 'SALUDABLE':
            return 'background-color: #d4edda; color: #155724;'
        elif val == 'ATENCIÓN':
            return 'background-color: #fff3cd; color: #856404;'
        elif val == 'VENCIDO':
            return 'background-color: #f8d7da; color: #721c24;'
        return ''

    try:
        styled_df = df_proyeccion_of_filtered.style.map(color_status_venc, subset=['Status Venc'])
    except AttributeError:
        styled_df = df_proyeccion_of_filtered.style.applymap(color_status_venc, subset=['Status Venc'])

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("### Totales del filtro actual")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Stock Unidades", f"{total_stock_unidades:,.2f}")
    col2.metric("Stock Kilos", f"{total_stock_kilos:,.2f}")
    col3.metric("Kilos Comprometidos", f"{total_comprometido:,.2f}")
    col4.metric("Kilos Pedidos a Prov", f"{total_pedidos:,.2f}")
    col5.metric("Kilos Disponibles", f"{total_saldo_disponible:,.2f}")


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
    temperature=0.2,
    max_tokens=1024,
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
    
    system_prompt = f"""Eres un asistente experto en análisis de datos con pandas. 
El usuario te hará preguntas sobre un dataframe de inventario.
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
            if "code" in msg:
                with st.expander("📝 Código generado", expanded=False):
                    st.code(msg["code"], language="python")
            if "error" in msg and msg["error"]:
                st.error(msg["error"])
            elif "result" in msg:
                result = msg["result"]
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"**Resultado:** {result}")

# Input de la pregunta
user_question = st.chat_input("Pregunta sobre el inventario... Ej: ¿Cuántos artículos vencidos hay?")

if user_question:
    # Agregar pregunta del usuario al historial
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando tu pregunta..."):
            try:
                code = ask_dataframe(user_question, df_proyeccion_of_filtered)
                
                with st.expander("📝 Código generado", expanded=False):
                    st.code(code, language="python")
                
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
