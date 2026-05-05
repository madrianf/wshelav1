"""
OTIF Calculator
===============
Calcula el indicador OTIF (On Time In Full) desde dos DataFrames:
    - df_pedidos  : tabla maestra de pedidos
    - df_entregas : tabla de entregas reales

Parámetros de periodicidad: 'semanal', 'mensual', 'anual'

Campos requeridos
-----------------
df_pedidos:
    pedido_id                  : str/int  – clave primaria
    fecha_pedido               : datetime
    fecha_entrega_comprometida : datetime – fecha pactada con el cliente
    cantidad_pedida            : float    – unidades/volumen comprometido

df_entregas:
    entrega_id                 : str/int  – clave primaria
    pedido_id                  : str/int  – FK a pedidos
    fecha_entrega_real         : datetime – cuándo llegó físicamente
    cantidad_entregada         : float    – unidades/volumen entregado
    estado_entrega             : str      – 'completa' | 'parcial' | 'fallida'

Ejemplo: Pedido entregado en 3 entregas parciales, todas a tiempo
------------------------------------------------------------------
Supongamos el siguiente pedido:
    pedido_id = "PED-00100"
    fecha_entrega_comprometida = 2025-03-15
    cantidad_pedida = 300 unidades

Y tres entregas registradas:
    ENT-001  → fecha_real: 2025-03-10, cantidad: 100, estado: "parcial"
    ENT-002  → fecha_real: 2025-03-13, cantidad: 120, estado: "parcial"
    ENT-003  → fecha_real: 2025-03-15, cantidad:  80, estado: "completa"

Paso 1 – Consolidación (líneas 120-128 del código):
    Se agrupan las entregas por pedido_id:
      • fecha_entrega_real  = max(2025-03-10, 2025-03-13, 2025-03-15) = 2025-03-15
      • cantidad_entregada  = sum(100 + 120 + 80) = 300
      • n_entregas          = 3

Paso 2 – Flag "On Time" (líneas 142-150):
    fecha_limite = fecha_entrega_comprometida + tolerancia_dias
    Con tolerancia_dias = 0:
      fecha_limite = 2025-03-15
    ¿fecha_entrega_real (2025-03-15) <= fecha_limite (2025-03-15)? → SÍ
    flag_on_time = True

Paso 3 – Flag "In Full" (líneas 152-154):
    umbral_cantidad = cantidad_pedida × (1 - tolerancia_cantidad_pct)
    Con tolerancia_cantidad_pct = 0.0:
      umbral_cantidad = 300 × 1.0 = 300
    ¿cantidad_entregada (300) >= umbral_cantidad (300)? → SÍ
    flag_in_full = True

Paso 4 – Flag "OTIF" (línea 157):
    flag_otif = flag_on_time AND flag_in_full = True AND True = True

Resultado: El pedido PED-00100 se marca como OTIF = True.

NOTA IMPORTANTE: Para la evaluación "On Time" se usa la fecha de la
ÚLTIMA entrega (max). Esto significa que si alguna de las tres entregas
hubiera llegado después de la fecha comprometida (por ejemplo, la tercera
el 2025-03-17), TODO el pedido se marcaría como flag_on_time = False,
incluso si las dos primeras entregas fueron puntuales. Del mismo modo,
para "In Full" se usa la SUMA de cantidades de todas las entregas, por lo
que si la suma total queda por debajo del umbral, el pedido no cumple
aunque cada entrega individual haya sido razonable.

Retorna
-------
Un dict con DataFrames de resultados por periodo y un DataFrame detallado
con los flags OT, IF y OTIF por cada pedido.
"""

import pandas as pd
import numpy as np
from typing import Literal


# ---------------------------------------------------------------------------
# Constantes de tolerancia
# ---------------------------------------------------------------------------
TOLERANCE_DIAS: int = 0          # días de gracia para "On Time" (0 = estricto)
TOLERANCE_PCT_CANTIDAD: float = 0.0  # % de tolerancia en cantidad (0 = estricto)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
def calcular_otif(
    df_pedidos: pd.DataFrame,
    df_entregas: pd.DataFrame,
    periodo: Literal["semanal", "mensual", "anual"] = "mensual",
    fecha_referencia: str = "fecha_entrega_comprometida",
    tolerancia_dias: int = TOLERANCE_DIAS,
    tolerancia_cantidad_pct: float = TOLERANCE_PCT_CANTIDAD,
    incluir_fallidas: bool = False,
) -> dict:
    """
    Calcula el OTIF por periodo (semanal / mensual / anual).

    Parameters
    ----------
    df_pedidos : pd.DataFrame
        Tabla de pedidos con columnas obligatorias descritas en el módulo.
    df_entregas : pd.DataFrame
        Tabla de entregas con columnas obligatorias descritas en el módulo.
    periodo : {'semanal', 'mensual', 'anual'}
        Granularidad del reporte.
    fecha_referencia : str
        Columna de df_pedidos usada para agrupar: 'fecha_pedido' o
        'fecha_entrega_comprometida'. Por defecto usa la fecha comprometida.
    tolerancia_dias : int
        Días de gracia extra para considerar una entrega "On Time".
        0 = modo estricto.
    tolerancia_cantidad_pct : float
        Porcentaje de tolerancia en cantidad para considerar "In Full".
        0.0 = modo estricto (ej.: 0.05 acepta hasta 5 % de faltante).
    incluir_fallidas : bool
        Si False (default), las entregas con estado_entrega='fallida' se
        tratan como 0 unidades entregadas. Si True, se excluyen del merge
        y el pedido queda sin entrega registrada.

    Returns
    -------
    dict con claves:
        'detalle'  : DataFrame fila-por-pedido con flags OT, IF, OTIF
        'resumen'  : DataFrame agrupado por periodo con % OT, % IF, % OTIF
        'metadata' : dict con parámetros usados en el cálculo
    """

    # ------------------------------------------------------------------
    # 1. Validaciones y normalización de tipos
    # ------------------------------------------------------------------
    df_pedidos = df_pedidos.copy()
    df_entregas = df_entregas.copy()

    _validar_columnas(df_pedidos, df_entregas)

    for col in ["fecha_pedido", "fecha_entrega_comprometida"]:
        df_pedidos[col] = pd.to_datetime(df_pedidos[col], errors="coerce")

    df_entregas["fecha_entrega_real"] = pd.to_datetime(
        df_entregas["fecha_entrega_real"], errors="coerce"
    )
    df_pedidos["cantidad_pedida"] = pd.to_numeric(
        df_pedidos["cantidad_pedida"], errors="coerce"
    )
    df_entregas["cantidad_entregada"] = pd.to_numeric(
        df_entregas["cantidad_entregada"], errors="coerce"
    )

    # ------------------------------------------------------------------
    # 2. Consolidar entregas por pedido
    #    Un pedido puede tener varias entregas parciales → sumamos
    # ------------------------------------------------------------------
    if not incluir_fallidas:
        # Las fallidas aportan 0 unidades
        df_entregas.loc[
            df_entregas["estado_entrega"] == "fallida", "cantidad_entregada"
        ] = 0.0

    # Fecha de entrega real = la ÚLTIMA entrega efectiva por pedido
    entregas_agg = (
        df_entregas.groupby("pedido_id")
        .agg(
            fecha_entrega_real=("fecha_entrega_real", "max"),
            cantidad_entregada=("cantidad_entregada", "sum"),
            n_entregas=("entrega_id", "count"),
        )
        .reset_index()
    )

    # ------------------------------------------------------------------
    # 3. Join pedidos ↔ entregas
    # ------------------------------------------------------------------
    df = df_pedidos.merge(entregas_agg, on="pedido_id", how="left")

    # Pedidos sin ninguna entrega = no entregados (peor caso para OTIF)
    df["cantidad_entregada"] = df["cantidad_entregada"].fillna(0.0)
    df["n_entregas"] = df["n_entregas"].fillna(0).astype(int)

    # ------------------------------------------------------------------
    # 4. Calcular flags OT e IF
    # ------------------------------------------------------------------
    fecha_limite = df["fecha_entrega_comprometida"] + pd.Timedelta(
        days=tolerancia_dias
    )

    # On Time: entrega real existe y llega antes/en la fecha límite
    df["flag_on_time"] = (
        df["fecha_entrega_real"].notna()
        & (df["fecha_entrega_real"] <= fecha_limite)
    )

    # In Full: cantidad entregada ≥ cantidad pedida × (1 - tolerancia)
    umbral_cantidad = df["cantidad_pedida"] * (1 - tolerancia_cantidad_pct)
    df["flag_in_full"] = df["cantidad_entregada"] >= umbral_cantidad

    # OTIF: ambas condiciones simultáneas
    df["flag_otif"] = df["flag_on_time"] & df["flag_in_full"]

    # Días de desviación (positivo = tarde, negativo = adelantado)
    df["dias_desviacion"] = (
        df["fecha_entrega_real"] - df["fecha_entrega_comprometida"]
    ).dt.days

    # % cumplimiento en cantidad
    df["pct_cantidad"] = np.where(
        df["cantidad_pedida"] > 0,
        (df["cantidad_entregada"] / df["cantidad_pedida"] * 100).round(2),
        np.nan,
    )

    # ------------------------------------------------------------------
    # 5. Agrupar por periodo
    # ------------------------------------------------------------------
    freq_map = {
        "semanal": ("W-MON", "%Y-W%V"),   # ISO week
        "mensual": ("MS",    "%Y-%m"),
        "anual":   ("YS",    "%Y"),
    }
    freq, fmt = freq_map[periodo]

    col_ref = fecha_referencia
    df["periodo"] = df[col_ref].dt.to_period(
        {"semanal": "W", "mensual": "M", "anual": "Y"}[periodo]
    )
    df["periodo_label"] = df[col_ref].dt.strftime(fmt)

    resumen = (
        df.groupby(["periodo", "periodo_label"])
        .agg(
            total_pedidos=("pedido_id", "count"),
            pedidos_on_time=("flag_on_time", "sum"),
            pedidos_in_full=("flag_in_full", "sum"),
            pedidos_otif=("flag_otif", "sum"),
        )
        .reset_index()
        .sort_values("periodo")
    )

    resumen["pct_on_time"] = (
        resumen["pedidos_on_time"] / resumen["total_pedidos"] * 100
    ).round(2)
    resumen["pct_in_full"] = (
        resumen["pedidos_in_full"] / resumen["total_pedidos"] * 100
    ).round(2)
    resumen["pct_otif"] = (
        resumen["pedidos_otif"] / resumen["total_pedidos"] * 100
    ).round(2)

    resumen = resumen.drop(columns=["periodo"])  # queda solo el label legible

    # ------------------------------------------------------------------
    # 6. Totales generales
    # ------------------------------------------------------------------
    n_total = len(df)
    totales = {
        "total_pedidos": n_total,
        "pct_on_time_global":  round(df["flag_on_time"].sum() / n_total * 100, 2),
        "pct_in_full_global":  round(df["flag_in_full"].sum() / n_total * 100, 2),
        "pct_otif_global":     round(df["flag_otif"].sum()    / n_total * 100, 2),
    }

    metadata = {
        "periodo": periodo,
        "fecha_referencia": fecha_referencia,
        "tolerancia_dias": tolerancia_dias,
        "tolerancia_cantidad_pct": tolerancia_cantidad_pct,
        **totales,
    }

    return {
        "detalle": df,
        "resumen": resumen,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Helper: validación de columnas mínimas
# ---------------------------------------------------------------------------
def _validar_columnas(df_pedidos: pd.DataFrame, df_entregas: pd.DataFrame) -> None:
    cols_pedidos = {
        "pedido_id",
        "fecha_pedido",
        "fecha_entrega_comprometida",
        "cantidad_pedida",
    }
    cols_entregas = {
        "entrega_id",
        "pedido_id",
        "fecha_entrega_real",
        "cantidad_entregada",
        "estado_entrega",
    }
    faltantes_p = cols_pedidos - set(df_pedidos.columns)
    faltantes_e = cols_entregas - set(df_entregas.columns)

    if faltantes_p:
        raise ValueError(f"df_pedidos le faltan columnas: {faltantes_p}")
    if faltantes_e:
        raise ValueError(f"df_entregas le faltan columnas: {faltantes_e}")


# ---------------------------------------------------------------------------
# Función de reporte rápido en consola
# ---------------------------------------------------------------------------
def imprimir_reporte(resultado: dict) -> None:
    meta = resultado["metadata"]
    resumen = resultado["resumen"]

    print("=" * 62)
    print(f"  REPORTE OTIF — Periodo: {meta['periodo'].upper()}")
    print("=" * 62)
    print(f"  Total pedidos analizados : {meta['total_pedidos']:,}")
    print(f"  On Time global           : {meta['pct_on_time_global']:.1f} %")
    print(f"  In Full global           : {meta['pct_in_full_global']:.1f} %")
    print(f"  OTIF global              : {meta['pct_otif_global']:.1f} %")
    print(f"  Tolerancia días          : {meta['tolerancia_dias']}")
    print(f"  Tolerancia cantidad      : {meta['tolerancia_cantidad_pct']*100:.1f} %")
    print("-" * 62)

    cols_show = [
        "periodo_label",
        "total_pedidos",
        "pct_on_time",
        "pct_in_full",
        "pct_otif",
    ]
    print(
        resumen[cols_show]
        .rename(
            columns={
                "periodo_label": "Periodo",
                "total_pedidos": "Pedidos",
                "pct_on_time":   "OT %",
                "pct_in_full":   "IF %",
                "pct_otif":      "OTIF %",
            }
        )
        .to_string(index=False)
    )
    print("=" * 62)


# ---------------------------------------------------------------------------
# Ejemplo de uso con datos sintéticos
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    from datetime import datetime, timedelta

    random.seed(42)
    np.random.seed(42)

    # --- Generar pedidos sintéticos (5 años) ---
    n_pedidos = 2000
    start = datetime(2020, 1, 1)

    pedido_ids = [f"PED-{i:05d}" for i in range(1, n_pedidos + 1)]
    fechas_pedido = [start + timedelta(days=random.randint(0, 365 * 5)) for _ in range(n_pedidos)]
    lead_times = np.random.randint(3, 30, n_pedidos)
    fechas_compromiso = [
        fechas_pedido[i] + timedelta(days=int(lead_times[i]))
        for i in range(n_pedidos)
    ]
    cantidades = np.random.uniform(50, 500, n_pedidos).round(2)

    df_pedidos = pd.DataFrame(
        {
            "pedido_id": pedido_ids,
            "cliente_id": [f"CLI-{random.randint(1,50):03d}" for _ in range(n_pedidos)],
            "fecha_pedido": fechas_pedido,
            "fecha_entrega_comprometida": fechas_compromiso,
            "producto_id": [f"PROD-{random.randint(1,20):02d}" for _ in range(n_pedidos)],
            "cantidad_pedida": cantidades,
            "unidad_medida": "unidades",
        }
    )

    # --- Generar entregas sintéticas ---
    # ~5 % de pedidos sin entrega, ~15 % parciales, ~10 % tarde
    registros_entrega = []
    for idx, row in df_pedidos.iterrows():
        r = random.random()
        if r < 0.05:          # sin entrega
            continue
        estado = "completa"
        retraso = np.random.choice([-3, -2, -1, 0, 0, 0, 1, 2, 3, 5, 8], p=[.05,.05,.08,.15,.15,.12,.10,.08,.08,.07,.07])
        fecha_real = row["fecha_entrega_comprometida"] + timedelta(days=int(retraso))
        if r < 0.15:
            cantidad = row["cantidad_pedida"] * random.uniform(0.5, 0.95)
            estado = "parcial"
        else:
            cantidad = row["cantidad_pedida"] * random.uniform(0.99, 1.01)

        registros_entrega.append(
            {
                "entrega_id": f"ENT-{idx:06d}",
                "pedido_id": row["pedido_id"],
                "fecha_entrega_real": fecha_real,
                "cantidad_entregada": round(cantidad, 2),
                "estado_entrega": estado,
                "transportista_id": f"TRANS-{random.randint(1,5):02d}",
            }
        )

    df_entregas = pd.DataFrame(registros_entrega)

    # --- Calcular OTIF en los tres periodos ---
    for p in ("semanal", "mensual", "anual"):
        resultado = calcular_otif(
            df_pedidos,
            df_entregas,
            periodo=p,
            tolerancia_dias=1,           # 1 día de gracia
            tolerancia_cantidad_pct=0.02, # 2 % de tolerancia en cantidad
        )
        imprimir_reporte(resultado)
        print()

    # --- Acceso programático al detalle ---
    detalle = resultado["detalle"]
    print("\nPrimeras 5 filas del detalle:")
    print(
        detalle[
            [
                "pedido_id",
                "fecha_entrega_comprometida",
                "fecha_entrega_real",
                "cantidad_pedida",
                "cantidad_entregada",
                "flag_on_time",
                "flag_in_full",
                "flag_otif",
                "dias_desviacion",
                "pct_cantidad",
            ]
        ]
        .head()
        .to_string()
    )