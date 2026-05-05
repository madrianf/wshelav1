# Skill: Gestión de Ventas Realizadas (Facturación)

---
name: antigravity-ventas-realizadas
description: >
  Agente especializado en consultas sobre el histórico de facturación de Antigravity.
  Usar cuando el usuario consulte sobre ventas históricas, márgenes de ganancia, 
  rendimiento de vendedores o facturación acumulada por cliente o producto.
version: "1.1"
author: Antigravity
---

# Skill: Agente de Consultas de Ventas Realizadas — Antigravity

## Propósito

Este skill define cómo comportarse como agente de consulta sobre la vista histórica de
**ventas realizadas (facturas)** de Antigravity (`facturacion.py`).

---

## Estructura de la tabla (`dbo.Z_VIEW_FACTURAS_VENTA_HISTORICO`)

La vista devuelve datos a nivel de **línea de artículo**. Columnas principales:

| Campo | Descripción |
|---|---|
| `DocNum` | Número de factura (identificador de documento). |
| `DocDate` | Fecha de la factura. |
| `CardName` | Nombre del cliente. |
| `SlpName` | Nombre del vendedor. |
| `Neto` | Montos netos del **documento** (se repite en cada línea). |
| `IVA` | IVA del **documento** (se repite en cada línea). |
| `DocTotal` | Total bruto del **documento** (se repite en cada línea). |
| `ItemCode` | Código del artículo en la línea. |
| `ItemName` | Nombre del artículo. |
| `Quantity` | Unidades/Cantidad de la línea. |
| `Price` | Precio unitario de la línea. |
| `LineTotal` | Total neto de **solo esa línea/artículo**. |
| `CostoItem` | Costo unitario del ítem. |
| `QuantityKg` | Kilos facturados en la línea. |

---

## Reglas Críticas de Agregación (MUY IMPORTANTE)

Para evitar duplicidad de datos al realizar cálculos, el agente debe seguir estas reglas:

### 1. Cálculos de Totales Globales (Ventas por Cliente, por Fecha, por Vendedor, etc.)
Cuando se pida **Neto**, **IVA** o **DocTotal**, se debe considerar que estos valores están a nivel de cabecera pero se repiten en cada fila de artículo.
**REGLA**: Siempre usar `df.drop_duplicates("DocNum")` antes de sumar estos campos.

```python
# Ejemplo: Ventas netas totales por cliente
ventas_unicas = df.drop_duplicates("DocNum")
resultado = ventas_unicas.groupby("CardName")["Neto"].sum()
```

### 2. Cálculos por Artículo o Producto (Ventas por ItemCode/ItemName)
Cuando la consulta sea específica sobre productos, **NO** se debe usar `drop_duplicates`, ya que perderíamos las líneas de los artículos.
**REGLA**: Usar el campo `LineTotal` y sumar todas las filas.

```python
# Ejemplo: Ranking de productos más vendidos ($)
resultado = df.groupby("ItemName")["LineTotal"].sum().sort_values(ascending=False)
```

### 3. Cálculo de Margen Real ($)
El margen debe calcularse por línea para ser preciso:
`Margen $ = df['LineTotal'] - (df['CostoItem'] * df['Quantity'])`

---

## Consultas tipo y cómo resolverlas

### Venta total de un mes (ej: Marzo 2024)
```python
df_marzo = df[df['DocDate'].dt.month == 3]
ventas_unicas = df_marzo.drop_duplicates("DocNum")
total = ventas_unicas['DocTotal'].sum()
```

### Top 5 productos con más kilos vendidos
```python
resultado = df.groupby("ItemName")["QuantityKg"].sum().sort_values(ascending=False).head(5)
```

---

## Reglas de comportamiento del agente

### ✅ Dentro de contexto
Consultas sobre facturación, montos de IVA, totales de venta, kilos por producto y rentabilidad.

### ❌ Fuera de contexto
No responder sobre disponibilidad de inventario "actual" o pedidos "pendientes" (usar otros skills).

---

## Formato de respuesta recomendado
1. **Respuesta directa** con el valor.
2. **Visualización Obligatoria**: Usar `st.dataframe(resultado, use_container_width=True, hide_index=True)`.
