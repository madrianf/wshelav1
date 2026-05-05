# Directorio de Skills

Aquí se almacenan todas las funcionalidades modulares del sistema.

- **common/**: Utilidades compartidas.
- **templates/**: Modelos para nuevas implementaciones.
- **[skill_name]/**: Carpetas individuales para cada habilidad.

## Instrucciones para el Agente AI
- Siempre que se abra o se trabaje en el archivo `pages/ventas y clientes/pedidos.py`, el agente AI **DEBE CONSULTAR Y USAR** obligatoriamente el skill ubicado en `skills/pedidos/PEDIDOS.md` como referencia principal para reglas de negocio y estructura de datos.

- Siempre que se abra o se trabaje en el archivo `pages/ventas y clientes/pedidosporfacturar.py`, el agente AI **DEBE CONSULTAR Y USAR** obligatoriamente el skill ubicado en `skills/pedidosxfacturar/PEDIDOSXFACTURAR.md` como referencia principal para reglas de negocio y estructura de datos.

- Siempre que se abra o se trabaje en el archivo `pages/ventas y clientes/facturacion.py`, el agente AI **DEBE CONSULTAR Y USAR** obligatoriamente el skill ubicado en `skills/ventasrealizadas/VENTASREALIZADAS.md` como referencia principal para reglas de negocio y estructura de datos.

- Siempre que se abra o se trabaje en los archivos `pages/ventas y clientes/disponibilidaddeinventario.py` o `pages/Producción y Logística/inventario.py`, el agente AI **DEBE CONSULTAR Y USAR** obligatoriamente el skill ubicado en `skills/inventario/INVENTARIO.md` como referencia principal para reglas de negocio y estructura de datos.