"""
calculus.py
-----------
Módulo de cálculo diferencial aplicado a series temporales ambientales.

Operaciones implementadas:
  - Derivada numérica (razón de cambio) por diferencias finitas centrales
  - Puntos críticos (donde la derivada cambia de signo)
  - Máximos y mínimos locales
  - Regresión lineal (pendiente, intercepto, R², tendencia)

Todas las funciones operan sobre pd.Series con índice datetime y
devuelven estructuras listas para serializar a JSON.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


# ─── Derivada numérica (razón de cambio) ─────────────────────────────────────

def derivada_numerica(
    series: pd.Series,
    timestamps: pd.Series,
) -> pd.Series:
    """
    Calcula dy/dt usando diferencias finitas centrales.

    Para los extremos usa diferencias hacia adelante/atrás.
    El tiempo se expresa en horas para que las unidades sean
    [unidad_variable / hora].

    Parameters
    ----------
    series     : valores numéricos (y)
    timestamps : columna datetime correspondiente

    Returns
    -------
    pd.Series con la derivada en cada punto (NaN donde y es NaN).
    """
    # Convertir timestamps a horas desde el primer registro
    t_hours = (timestamps - timestamps.iloc[0]).dt.total_seconds() / 3600.0
    y = series.values.astype(float)
    t = t_hours.values.astype(float)

    n = len(y)
    dy = np.full(n, np.nan)

    for i in range(n):
        y_i = y[i]
        if np.isnan(y_i):
            continue

        # Buscar vecino anterior válido
        prev_idx = next((j for j in range(i - 1, -1, -1) if not np.isnan(y[j])), None)
        # Buscar vecino siguiente válido
        next_idx = next((j for j in range(i + 1, n) if not np.isnan(y[j])), None)

        if prev_idx is not None and next_idx is not None:
            # Diferencia central
            dt = t[next_idx] - t[prev_idx]
            if dt != 0:
                dy[i] = (y[next_idx] - y[prev_idx]) / dt
        elif next_idx is not None:
            # Diferencia hacia adelante
            dt = t[next_idx] - t[i]
            if dt != 0:
                dy[i] = (y[next_idx] - y_i) / dt
        elif prev_idx is not None:
            # Diferencia hacia atrás
            dt = t[i] - t[prev_idx]
            if dt != 0:
                dy[i] = (y_i - y[prev_idx]) / dt

    return pd.Series(dy, index=series.index)


# ─── Puntos críticos ─────────────────────────────────────────────────────────

def puntos_criticos(
    series: pd.Series,
    timestamps: pd.Series,
    dy: pd.Series | None = None,
) -> list[dict]:
    """
    Detecta puntos críticos donde la derivada cambia de signo.

    Un punto crítico indica:
      - Cambio de positivo → negativo : máximo local
      - Cambio de negativo → positivo : mínimo local
      - Cruce por cero de la derivada : punto de inflexión candidato

    Returns
    -------
    Lista de dicts con:
      datetime, valor, tipo (maximo_local | minimo_local | inflexion),
      derivada_antes, derivada_despues
    """
    if dy is None:
        dy = derivada_numerica(series, timestamps)

    puntos: list[dict] = []
    dy_vals = dy.values
    y_vals  = series.values
    ts_vals = timestamps.values
    n = len(dy_vals)

    for i in range(1, n - 1):
        d_prev = dy_vals[i - 1]
        d_curr = dy_vals[i]
        d_next = dy_vals[i + 1]

        if np.isnan(d_prev) or np.isnan(d_curr) or np.isnan(y_vals[i]):
            continue

        # Cambio de signo entre i-1 e i
        if d_prev * d_curr < 0 or (d_prev != 0 and d_curr == 0):
            if d_prev > 0 and (d_curr < 0 or (d_curr == 0 and not np.isnan(d_next) and d_next < 0)):
                tipo = "maximo_local"
            elif d_prev < 0 and (d_curr > 0 or (d_curr == 0 and not np.isnan(d_next) and d_next > 0)):
                tipo = "minimo_local"
            else:
                tipo = "inflexion"

            puntos.append({
                "datetime":         pd.Timestamp(ts_vals[i]).isoformat(),
                "valor":            _r(float(y_vals[i])),
                "tipo":             tipo,
                "derivada_antes":   _r(float(d_prev)),
                "derivada_despues": _r(float(d_next)) if not np.isnan(d_next) else None,
            })

    return puntos


# ─── Máximos y mínimos globales + locales ────────────────────────────────────

def extremos(
    series: pd.Series,
    timestamps: pd.Series,
    ventana: int = 5,
) -> dict:
    """
    Calcula:
      - Máximo y mínimo global (absoluto)
      - Máximos y mínimos locales usando ventana móvil

    Parameters
    ----------
    ventana : número de registros a cada lado para considerar un extremo local
    """
    clean     = series.dropna()
    clean_ts  = timestamps[clean.index]

    if clean.empty:
        return {
            "maximo_global": None, "minimo_global": None,
            "maximos_locales": [],  "minimos_locales": [],
        }

    idx_max = clean.idxmax()
    idx_min = clean.idxmin()

    # Máximos locales por ventana móvil
    rolling_max = clean.rolling(window=2 * ventana + 1, center=True, min_periods=1).max()
    rolling_min = clean.rolling(window=2 * ventana + 1, center=True, min_periods=1).min()

    max_locales = []
    min_locales = []

    for idx in clean.index:
        val = clean[idx]
        if val == rolling_max[idx] and val != rolling_min[idx]:
            max_locales.append({
                "datetime": pd.Timestamp(timestamps[idx]).isoformat(),
                "valor":    _r(float(val)),
            })
        elif val == rolling_min[idx] and val != rolling_max[idx]:
            min_locales.append({
                "datetime": pd.Timestamp(timestamps[idx]).isoformat(),
                "valor":    _r(float(val)),
            })

    return {
        "maximo_global": {
            "datetime": pd.Timestamp(timestamps[idx_max]).isoformat(),
            "valor":    _r(float(clean[idx_max])),
        },
        "minimo_global": {
            "datetime": pd.Timestamp(timestamps[idx_min]).isoformat(),
            "valor":    _r(float(clean[idx_min])),
        },
        "maximos_locales": max_locales,
        "minimos_locales": min_locales,
    }


# ─── Regresión lineal y tendencia ────────────────────────────────────────────

def regresion_lineal(
    series: pd.Series,
    timestamps: pd.Series,
) -> dict:
    """
    Ajusta y = m·t + b donde t es tiempo en horas desde el inicio.

    Returns
    -------
    dict con:
      pendiente        : m  [unidad/hora]
      intercepto       : b  [unidad]
      r_cuadrado       : R² (0–1, calidad del ajuste)
      tendencia        : "creciente" | "decreciente" | "estable"
      prediccion_proxima_hora : valor estimado 1h después del último punto
      ecuacion         : string legible "y = m·t + b"
    """
    clean    = series.dropna()
    clean_ts = timestamps[clean.index]

    if len(clean) < 2:
        return {
            "pendiente": None, "intercepto": None,
            "r_cuadrado": None, "tendencia": None,
            "prediccion_proxima_hora": None, "ecuacion": None,
        }

    t = (clean_ts - clean_ts.iloc[0]).dt.total_seconds().values / 3600.0
    y = clean.values.astype(float)

    # Mínimos cuadrados
    n  = len(t)
    sx = float(np.sum(t))
    sy = float(np.sum(y))
    sxx= float(np.sum(t * t))
    sxy= float(np.sum(t * y))

    denom = n * sxx - sx * sx
    if denom == 0:
        return {
            "pendiente": 0.0, "intercepto": _r(float(np.mean(y))),
            "r_cuadrado": None, "tendencia": "estable",
            "prediccion_proxima_hora": _r(float(np.mean(y))), "ecuacion": None,
        }

    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n

    # R²
    y_pred  = m * t + b
    ss_res  = float(np.sum((y - y_pred) ** 2))
    ss_tot  = float(np.sum((y - np.mean(y)) ** 2))
    r2      = 1.0 - ss_res / ss_tot if ss_tot != 0 else 1.0

    # Tendencia
    umbral = 0.001  # cambios menores a esto se consideran estables
    if abs(m) < umbral:
        tendencia = "estable"
    elif m > 0:
        tendencia = "creciente"
    else:
        tendencia = "decreciente"

    # Predicción 1h después del último punto
    t_last = t[-1]
    pred   = m * (t_last + 1) + b

    return {
        "pendiente":               _r(m),
        "intercepto":              _r(b),
        "r_cuadrado":              _r(r2),
        "tendencia":               tendencia,
        "prediccion_proxima_hora": _r(pred),
        "ecuacion":                f"y = {_r(m)}·t + {_r(b)}",
    }


# ─── Análisis completo de una variable ───────────────────────────────────────

def analisis_completo(
    series: pd.Series,
    timestamps: pd.Series,
    variable: str,
    ventana_extremos: int = 5,
    max_puntos_criticos: int = 100,
    max_extremos_locales: int = 50,
) -> dict:
    """
    Ejecuta todos los análisis sobre una variable y devuelve un dict
    listo para serializar a JSON.

    Se aplican límites de registros devueltos para respuestas manejables.
    """
    clean_mask = series.notna()
    s  = series[clean_mask]
    ts = timestamps[clean_mask]

    if s.empty:
        return {
            "variable":        variable,
            "n_registros":     0,
            "derivada":        [],
            "puntos_criticos": [],
            "extremos":        {},
            "regresion":       {},
        }

    dy = derivada_numerica(s, ts)

    # Derivada: muestra cada N puntos para no saturar la respuesta
    step = max(1, len(s) // 500)   # máx 500 puntos de derivada
    dy_records = [
        {
            "datetime": pd.Timestamp(ts.iloc[i]).isoformat(),
            "valor":    _r(float(s.iloc[i])),
            "dy_dt":    _r(float(dy.iloc[i])) if not np.isnan(dy.iloc[i]) else None,
        }
        for i in range(0, len(s), step)
    ]

    criticos = puntos_criticos(s, ts, dy)[:max_puntos_criticos]
    ext      = extremos(s, ts, ventana=ventana_extremos)

    # Limitar extremos locales
    ext["maximos_locales"] = ext["maximos_locales"][:max_extremos_locales]
    ext["minimos_locales"] = ext["minimos_locales"][:max_extremos_locales]

    reg = regresion_lineal(s, ts)

    return {
        "variable":        variable,
        "n_registros":     len(s),
        "derivada":        dy_records,
        "puntos_criticos": criticos,
        "extremos":        ext,
        "regresion":       reg,
    }


# ─── Helper ──────────────────────────────────────────────────────────────────

def _r(val: float, decimales: int = 4) -> float:
    """Redondea a N decimales, devuelve None si es NaN/inf."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    return round(val, decimales)
