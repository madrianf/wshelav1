import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns   
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime   import datetime, timedelta

conn = st.connection("sqlserver", type="sql")
df_proyeccion_of = conn.query("""

DECLARE @YAPO VARCHAR(50) = CONVERT(VARCHAR(50), GETDATE(),101);
DECLARE @hoy DATETIME = SUBSTRING(@YAPO,7,4) + '-' + SUBSTRING(@YAPO,4,2) + '-' + SUBSTRING(@YAPO,1,2) + ' 00:00:00.000';

SELECT
    T0.ItemCode 'Código Artículo', T4.itemName 'Nombre de Artículo',
    T1.WhsCode as 'Almacén', T1.BinCode 'Ubicación', T4.DistNumber 'Lote', CASE WHEN T3.U_ARTI_GRUPO='1' THEN 'PRODUCTO TERMINADO' WHEN T3.U_ARTI_GRUPO='2' THEN 'MATERIA PRIMA' WHEN T3.U_ARTI_GRUPO='5' THEN 'INSUMO EMBALAJE' WHEN T3.U_ARTI_GRUPO='3' THEN 'REVENTA' WHEN T3.U_ARTI_GRUPO='4' THEN 'SEMI ELABORADO' END AS Grupo , T5.ItmsGrpNam AS 'Categoria', 
CASE 
WHEN T3.U_ARTI_CATEGORIA='1' THEN  'Mezcla De Fosfatos'
WHEN T3.U_ARTI_CATEGORIA='2' THEN  'Antioxidante'
WHEN T3.U_ARTI_CATEGORIA='3' THEN  'Sales De Cura Y Nitrificada'
WHEN T3.U_ARTI_CATEGORIA='4' THEN  'Preservante / Bacteriostático / Fungistático'
WHEN T3.U_ARTI_CATEGORIA='5' THEN  'Colorantes'
WHEN T3.U_ARTI_CATEGORIA='6' THEN  'Otros'
WHEN T3.U_ARTI_CATEGORIA='7' THEN  'Salmuera'
WHEN T3.U_ARTI_CATEGORIA='8' THEN  'Proteinas Vegetales, Animales Y Fibras'
WHEN T3.U_ARTI_CATEGORIA='9' THEN  'Empanizador Y Batidos'
WHEN T3.U_ARTI_CATEGORIA='10' THEN  'Especias'
WHEN T3.U_ARTI_CATEGORIA='11' THEN  'Vegetal Deshidratado'
WHEN T3.U_ARTI_CATEGORIA='12' THEN  'Solubles'
WHEN T3.U_ARTI_CATEGORIA='13' THEN  'Condimento'
WHEN T3.U_ARTI_CATEGORIA='14' THEN  'Aplicaciones Dulces'
WHEN T3.U_ARTI_CATEGORIA='15' THEN  'Liofilizado'
WHEN T3.U_ARTI_CATEGORIA='16' THEN  'Mallas'
WHEN T3.U_ARTI_CATEGORIA='17' THEN  'Salsas'
WHEN T3.U_ARTI_CATEGORIA='18' THEN  'Compound'
WHEN T3.U_ARTI_CATEGORIA='19' THEN  'Sabores'
WHEN T3.U_ARTI_CATEGORIA='20' THEN  'Extractos De Levadura Y Levadura Nutricional'
WHEN T3.U_ARTI_CATEGORIA='21' THEN  'Semillas'
WHEN T3.U_ARTI_CATEGORIA='22' THEN  'Oleorresinas'
WHEN T3.U_ARTI_CATEGORIA='23' THEN  'Hela Alemania'
ELSE ''
END AS 'Categoría Nueva'
, T2.onHandQty 'Stock Unidades' 
, (T2.onHandQty * (T3.U_ARTI_FACTOR_KILO * T3.U_ARTI_TOTAL_X_UNIDPRODUCCION)) 'Stock Kilos'
, T4.[InDate], T4.[ExpDate]
, DATEDIFF(day, @hoy, T4.[ExpDate]) 'Dias Venc'
, DATEDIFF(MONTH, @hoy, T4.[ExpDate]) 'Meses Venc'
, CASE WHEN DATEDIFF(MONTH,  @hoy, T4.[ExpDate]) < 0 THEN 'VENCIDO' WHEN DATEDIFF(MONTH,   @hoy, T4.[ExpDate]) <= 3 THEN 'ATENCIÓN' WHEN DATEDIFF(MONTH,  @hoy, T4.[ExpDate]) > 3 THEN 'SALUDABLE' ELSE '' END 'Status Venc'
, T3.[AvgPrice] 'Costo Unitario', (T3.[AvgPrice] * T2.onHandQty ) 'Costo Total'
, (T3.[AvgPrice] / (ISNULL(T3.U_ARTI_TOTAL_X_UNIDPRODUCCION, 1) * ISNULL(T3.U_ARTI_FACTOR_KILO, 1) )) 'Costo por Kilo'
from
    OIBQ T0 
    inner join OBIN T1 on (T0.BinAbs = T1.AbsEntry and T0.onHandQty <> 0)
    left outer join OITM T3 ON (T0.ItemCode = t3.ItemCode)
    inner join OITB T5 ON (T3.ItmsGrpCod = T5.ItmsGrpCod)
    left outer join OBBQ T2 on (T0.BinAbs = T2.BinAbs and T0.ItemCode = T2.ItemCode)
    left outer join OBTN T4 on (T2.SnBMDAbs = T4.AbsEntry and T2.ItemCode = T4.ItemCode)
where
    T1.AbsEntry >= 0 
    and T2.onHandQty > 0
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
    background-color: #060606 !important;
    color: white !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #1c1b31 !important; 
}
</style>
""", unsafe_allow_html=True)

st.markdown("# Existencias")
st.write("Lista de inventario con articulos saldo > 0")
st.markdown("---")

df_proyeccion_of_filtered = df_proyeccion_of.copy()

with st.expander("Filtros por Columna", expanded=True):
    filtros_permitidos = ['Almacén', 'Grupo', 'Categoria', 'Código Artículo', 'Nombre de Artículo', 'Status Venc']
    cols = st.columns(len(filtros_permitidos))
    for i, col_name in enumerate(filtros_permitidos):
        if col_name in df_proyeccion_of.columns:
            with cols[i]:
                search_val = st.text_input(col_name, key=f"search_{col_name}", placeholder="...")
                if search_val:
                    df_proyeccion_of_filtered = df_proyeccion_of_filtered[
                        df_proyeccion_of_filtered[col_name].astype(str).str.contains(search_val, case=False, na=False)
                    ]

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

# Ocultar el índice explícitamente en el objeto Styler (compatible con varias versiones de Pandas)
try:
    styled_df = styled_df.hide(axis="index")
except AttributeError:
    styled_df = styled_df.hide_index()

st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.sidebar.header("Opciones")   
st.sidebar.markdown("---")

st.sidebar.button("Pedidos", use_container_width=True, type="primary", on_click=None)
st.sidebar.button("Inventario", use_container_width=True, type="primary", on_click=None)
st.sidebar.button("Ordenes de Fabricacion", use_container_width=True, type="primary", on_click=None)
st.sidebar.button("Ventas", use_container_width=True, type="primary", on_click=None)



