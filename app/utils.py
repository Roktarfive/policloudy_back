"""
utils.py
--------
Funciones de utilidad compartidas entre los routers:
  - Obtención del DataFrame activo con manejo de error HTTP amigable.
  - Filtrado por rango de fechas e IDs.
  - Cálculo de estadísticas (promedio, moda, max, min).
  - Serialización de DataFrames a lista de dicts eliminando NaN.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from fastapi import HTTPException

from app.data_store import get_df as _get_df
from app.schemas import EstadisticaVariable


# ─── Obtención segura del DataFrame activo ───────────────────────────────────

def require_df() -> pd.DataFrame:
    """
    Devuelve el DataFrame activo o lanza HTTP 503 si no hay datos cargados.
    Todos los routers de consulta deben usar esta función.
    """
    try:
        return _get_df()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


# ─── Filtrado ─────────────────────────────────────────────────────────────────

def filter_df(
    df: pd.DataFrame,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Filtra el DataFrame por:
      - Rango de fechas (fecha_inicio y/o fecha_fin, ambos inclusive).
      - Lista de IDs (índice 0-based asignado tras el sort en el parser).
    Todos los parámetros son opcionales y se combinan como AND.
    """
    result = df

    if fecha_inicio:
        result = result[result["datetime"].dt.date >= fecha_inicio]
    if fecha_fin:
        result = result[result["datetime"].dt.date <= fecha_fin]
    if ids:
        result = result[result.index.isin(ids)]

    return result


# ─── Serialización ────────────────────────────────────────────────────────────

def df_to_records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    """
    Convierte un DataFrame a lista de dicts con:
      - `id`       → índice original (estable dentro del dataset actual)
      - `datetime` → string ISO-8601
      - columnas solicitadas con NaN → None
    """
    available = [c for c in columns if c in df.columns]
    subset = df[["datetime"] + available].copy()
    subset.insert(0, "id", df.index)

    records = subset.where(subset.notna(), other=None).to_dict(orient="records")

    for rec in records:
        if rec.get("datetime") is not None:
            rec["datetime"] = rec["datetime"].isoformat()

    return records


# ─── Estadísticas ─────────────────────────────────────────────────────────────

def calc_estadistica(series: pd.Series) -> EstadisticaVariable:
    """
    Calcula promedio, máximo, mínimo y moda de una Serie numérica.
    Ignora NaN automáticamente. Devuelve campos None si la Serie está vacía.
    """
    clean = series.dropna()

    if clean.empty:
        return EstadisticaVariable()

    moda_result = clean.mode()
    moda = float(moda_result.iloc[0]) if not moda_result.empty else None

    return EstadisticaVariable(
        promedio=round(float(clean.mean()), 4),
        maximo=float(clean.max()),
        minimo=float(clean.min()),
        moda=moda,
    )
