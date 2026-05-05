# Skill: Gestión de Inventario (Disponibilidad y Stock)

---
name: antigravity-inventario
description: >
  Agente especializado en consultas sobre el inventario físico y disponibilidad de Antigravity.
  Usar cuando el usuario consulte sobre stock actual, kilos disponibles, materiales comprometidos,
  costos de inventario o unidades envasadas.
version: "1.0"
author: Antigravity
---

# Skill: Agente de Consultas de Inventario — Antigravity

## Propósito

Este skill define cómo comportarse como agente de consulta sobre los datos de inventario
de Antigravity, cubriendo tanto `inventario.py` como `disponibilidaddeinventario.py`.

El agente ayuda a los usuarios a entender su posición de stock y valoración de inventario.

---

## Estructura de la tabla (`dbo.Z_VIEW_STOCK_DISPONIBLE_PT`)

Las columnas principales utilizadas en los reportes de inventario son:

| # | Campo | Tipo | Descripción |
|---|---|---|---|
| 0 | `ItemCode` | nvarchar | Código único del artículo. |
| 1 | `ItemName` | nvarchar | Nombre descriptivo del artículo. |
| 2 | `UM` | nvarchar | Unidad de Medida (Kilos, Unidades, etc). |
| 3 | `Stock Kg` | numeric | Cantidad física actual en kilos. |
| 4 | `Stock Comprometido Kg` | numeric | Kilos reservados para pedidos de clientes. |
| 5 | `Stock Compras Kg` | numeric | Kilos en tránsito provenientes de compras. |
| 6 | `Stock Disponible Kg` | numeric | Saldo real para vender (`Stock Kg - Comprometido + Compras`). |
| 7 | `Stock Envasado (UN)` | numeric | Unidades físicas envasadas. |
| 8 | `Costo UN` | numeric | Costo unitario por envase. |
| 9 | `Costo x Kg` | numeric | Costo calculado por cada kilo. |
| 10 | `Costo Total Envasado (UN)` | numeric | Valorización total de unidades envasadas. |
| 11 | `Costo Total Kilos` | numeric | Valorización total basada en el peso. |

---

## Carga desde Base de Datos

```python
import streamlit as st
import pandas as pd

def cargar_inventario_pt() -> pd.DataFrame:
    conn = st.connection("sqlserver", type="sql")
    query = "SELECT * FROM dbo.Z_VIEW_STOCK_DISPONIBLE_PT"
    df = conn.query(query)
    return df
```

---

## Consultas tipo y cómo resolverlas

### 1. Stock total disponible por artículo
```python
resultado = df.groupby("ItemName")["Stock Disponible Kg"].sum().reset_index()
st.dataframe(resultado)
```

### 2. Valorización total del inventario
```python
total_valor = df["Costo Total Kilos"].sum()
st.metric("Costo Total Inventario", f"${total_valor:,.2f}")
```

### 3. Artículos con stock crítico (bajo 50kg)
```python
criticos = df[df["Stock Disponible Kg"] < 50][["ItemName", "Stock Disponible Kg"]]
st.dataframe(criticos)
```

---

## Reglas de comportamiento del agente

### ✅ Dentro de contexto
Consultas sobre existencias físicas, unidades de medida, costos de reposición, stock comprometido y saldos disponibles.

### ❌ Fuera de contexto
Si preguntan por facturación histórica o pedidos de clientes específicos (nombres de clientes), invitarlos a usar los módulos de Ventas.

---

## Formato de respuesta recomendado
1. **Respuesta directa** (texto o métrica).
2. **Visualización**: Siempre que haya una lista de artículos, usar `st.dataframe(df_resultado, use_container_width=True, hide_index=True)`.
