import streamlit as st

st.set_page_config(page_title="Hela-WorkSpaces", layout="wide")

# Branding en la barra lateral
st.sidebar.image("images/logo-hela.webp", use_container_width=True)
st.sidebar.markdown("<h4 style='text-align: center; color: #555; margin-top: -15px;'>HELA Spice LATAM S.A.</h4>", unsafe_allow_html=True)
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

inventario_page = st.Page("pages/Producción y Logística/inventario.py", title="Informe Inventario PT", icon="📦", default=True)
# dash_prod_page = st.Page("pages/Producción y Logística/dashboard.py", title="Panel de Control Producción", icon="📊")  # OCULTO
dash_logistica_page = st.Page("pages/Producción y Logística/dashboardlogistica.py", title="Panel de Control Logística", icon="🚛")
ordenes_page = st.Page("pages/Producción y Logística/ordenes.py", title="Informe de Producción", icon="⚙️")


dash_clientes_page = st.Page("pages/ventas y clientes/dashboardclientes.py", title="Dashboard Clientes", icon="👥", url_path="dashboard_clientes")
dash_pedidos_page = st.Page("pages/ventas y clientes/dashboardpedidos.py", title="Dashboard Pedidos", icon="📦", url_path="dashboard_pedidos")
dash_vendedores_page = st.Page("pages/ventas y clientes/dashboardvendedores.py", title="Dashboard Vendedores", icon="🧑", url_path="dashboard_vendedores")
pedidos_page = st.Page("pages/ventas y clientes/pedidos.py", title="Informe Pedidos en Sistema", icon="🛒")
facturacion_page = st.Page("pages/ventas y clientes/facturacion.py", title="Informe Ventas Realizadas", icon="💵")
pedidosporfacturar_page = st.Page("pages/ventas y clientes/pedidosporfacturar.py", title="Informe Pedidos por Facturar", icon="🧾")
disponibilidad_page = st.Page("pages/ventas y clientes/disponibilidaddeinventario.py", title="Informe Disponibilidad de Inventario", icon="📦")

pg = st.navigation(
    {
        "PRODUCCIÓN Y LOGÍSTICA": [ordenes_page, inventario_page, dash_logistica_page],
        "VENTAS Y CLIENTES": [dash_clientes_page, dash_pedidos_page, dash_vendedores_page, disponibilidad_page, pedidos_page, pedidosporfacturar_page, facturacion_page]
    },
    expanded=False
)

st.sidebar.markdown("---")

pg.run()
