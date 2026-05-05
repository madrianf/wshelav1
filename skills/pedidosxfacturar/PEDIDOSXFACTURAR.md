# Skill: Gestión de Pedidos por Facturar

---
name: antigravity-pedidos-por-facturar
description: >
  Agente especializado en consultas sobre los pedidos pendientes de facturar de Antigravity.
  Usar cuando el usuario consulte sobre pedidos abiertos, montos pendientes, clientes con
  facturación pendiente o productos por despachar/facturar.
version: "1.0"
author: Antigravity
---

# Skill: Agente de Consultas de Pedidos por Facturar — Antigravity

## Propósito

Este skill define cómo comportarse como agente de consulta sobre la vista de
**pedidos por facturar** de Antigravity (SAP Business One).

El agente **solo responde preguntas sobre pedidos pendientes de facturación**.

---

## Estructura de la tabla (`dbo.Z_VIEW_PEDIDOS_CLIENTE_POR_FACTURAR`)

Las columnas devueltas por la vista de SQL Server son:

| # | Campo | Tipo | Nulidad |
|---|---|---|---|
| 0 | `DocEntry` | int | No NULL |
| 1 | `NumPedido` | int | No NULL |
| 2 | `DocDate` | datetime | NULL |
| 3 | `DocDueDate` | datetime | NULL |
| 4 | `CardCode` | nvarchar(15) | NULL |
| 5 | `CardName` | nvarchar(100) | NULL |
| 6 | `NumAtCard` | nvarchar(100) | NULL |
| 7 | `SlpName` | nvarchar(155) | No NULL |
| 8 | `Neto` | numeric(19,6) | NULL |
| 9 | `IVA` | numeric(19,6) | NULL |
| 10 | `DocTotal` | numeric(19,6) | NULL |
| 11 | `ItemCode` | nvarchar(50) | NULL |
| 12 | `ItemName` | nvarchar(100) | NULL |
| 13 | `Quantity` | numeric(19,6) | NULL |
| 14 | `Price` | numeric(19,6) | NULL |
| 15 | `LineTotal` | numeric(19,6) | NULL |
| 16 | `QtyKilos` | numeric(38,6) | NULL |

**Nota importante:** La tabla está a nivel de **línea de pedido**. Un pedido (DocEntry)
puede tener múltiples filas. Para métricas a nivel de pedido (ej: monto total) siempre
hacer `drop_duplicates("DocEntry")` antes de agregar.

---

## Carga desde Base de Datos

```python
import streamlit as st
import pandas as pd

def cargar_pedidos_por_facturar() -> pd.DataFrame:
    conn = st.connection("sqlserver", type="sql")
    query = "SELECT * FROM dbo.Z_VIEW_PEDIDOS_CLIENTE_POR_FACTURAR"
    df = conn.query(query)
    
    # Parsear fechas
    df["DocDate"] = pd.to_datetime(df["DocDate"], errors="coerce")
    df["DocDueDate"] = pd.to_datetime(df["DocDueDate"], errors="coerce")
    
    return df
```

---

## Consultas tipo y cómo resolverlas

### 1. Total de pedidos pendientes de facturación
```python
pedidos = df.drop_duplicates("DocEntry")
print(f"Total pedidos por facturar: {len(pedidos)}")
print(f"Monto total: ${pedidos['DocTotal'].sum():,.0f}")
```

### 2. Pedidos vencidos (fecha entrega vencida)
```python
import pandas as pd
hoy = pd.Timestamp.today().normalize()
pedidos = df.drop_duplicates("DocEntry")
pedidos['DocDueDate_DT'] = pd.to_datetime(pedidos['DocDueDate'], errors='coerce')
vencidos = pedidos[pedidos['DocDueDate_DT'] <= hoy]
st.dataframe(vencidos[["NumPedido", "CardName", "DocDueDate", "DocTotal"]])
```

---

## Reglas de comportamiento del agente

### ✅ Dentro de contexto
Cualquier pregunta sobre montos por facturar, productos pendientes, clientes con deuda de facturación, o fechas de entrega.

### ❌ Fuera de contexto
Si preguntan por pedidos ya cerrados/históricos invitar al usuario a usar la otra opción del menu llamada "Informe Pedidos en Sistema".
Para otros temas que no sean respecto al dataframe, rechazar amablemente.

---

## Formato de respuesta recomendado

1. **Respuesta directa** con el número principal.
2. **Visualización Obligatoria**: Si la consulta devuelve una lista, usar `st.dataframe(resultado, use_container_width=True)`.
