"""
Endpoints de cálculo diferencial aplicado a las series temporales ambientales.

GET /analisis/variable
    Analiza una variable específica: derivada, puntos críticos,
    extremos y regresión lineal.

GET /analisis/completo
    Ejecuta el análisis completo sobre todas las variables principales
    en un rango de fechas.

GET /analisis/regresion
    Solo regresión lineal + tendencia para todas las variables.
    Respuesta más ligera, ideal para tarjetas de tendencia en el dashboard.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from app.calculus import analisis_completo, regresion_lineal
from app.data_store import NUMERIC_COLS
from app.schemas import (
    AnalisisCompletoResponse,
    AnalisisVariableResponse,
    ExtremosResult,
    RegresionLineal,
)
from app.utils import filter_df, require_df

router = APIRouter(prefix="/analisis", tags=["Cálculo Diferencial"])

# Variables principales para el análisis completo
_VARS_PRINCIPALES = [
    "barometro", "temperatura", "humedad", "viento_velocidad",
    "lluvia", "radiacion_solar", "indice_uv",
]

VariableEnum = Literal[
    "barometro", "temperatura", "humedad", "viento_velocidad",
    "temp_sensacion_min", "indice_calor", "et",
    "lluvia", "lluvia_intensidad_max", "radiacion_solar",
    "indice_uv", "dosis_uv",
]


# ─── Análisis de una variable ─────────────────────────────────────────────────

@router.get(
    "/variable",
    response_model=AnalisisVariableResponse,
    summary="Análisis diferencial de una variable",
    description="""
Calcula para la variable y rango de fechas indicados:

- **Derivada numérica** (razón de cambio dy/dt en unidad/hora) usando diferencias finitas centrales
- **Puntos críticos**: donde dy/dt cambia de signo → máximos locales, mínimos locales, inflexiones
- **Extremos globales y locales**: máximo y mínimo absoluto + extremos por ventana móvil
- **Regresión lineal**: pendiente, intercepto, R², tendencia y predicción a 1h
""",
)
def get_analisis_variable(
    variable:     VariableEnum = Query(..., description="Variable ambiental a analizar"),
    fecha_inicio: Optional[date] = Query(None, description="Inicio del rango (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fin del rango (YYYY-MM-DD)"),
    ventana:      int = Query(5, ge=1, le=50, description="Ventana para extremos locales (registros a cada lado)"),
) -> AnalisisVariableResponse:

    df  = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin)

    if df_f.empty:
        raise HTTPException(status_code=404, detail="No hay datos en el rango indicado.")

    if variable not in df_f.columns:
        raise HTTPException(status_code=404, detail=f"Variable '{variable}' no encontrada.")

    resultado = analisis_completo(
        series=df_f[variable],
        timestamps=df_f["datetime"],
        variable=variable,
        ventana_extremos=ventana,
    )

    return _dict_to_response(resultado)


# ─── Análisis completo (todas las variables) ──────────────────────────────────

@router.get(
    "/completo",
    response_model=AnalisisCompletoResponse,
    summary="Análisis diferencial completo de todas las variables",
    description="""
Ejecuta el análisis diferencial completo (derivada, puntos críticos, extremos
y regresión lineal) sobre **todas las variables principales** en el rango de fechas.

Variables incluidas: barometro, temperatura, humedad, viento_velocidad,
lluvia, radiacion_solar, indice_uv.

⚠️ Para rangos largos (> 30 días) puede tardar unos segundos.
""",
)
def get_analisis_completo(
    fecha_inicio: Optional[date] = Query(None, description="Inicio del rango (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fin del rango (YYYY-MM-DD)"),
    ventana:      int = Query(5, ge=1, le=50, description="Ventana para extremos locales"),
) -> AnalisisCompletoResponse:

    df   = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin)

    if df_f.empty:
        raise HTTPException(status_code=404, detail="No hay datos en el rango indicado.")

    resultados = {
        var: _dict_to_response(
            analisis_completo(
                series=df_f[var],
                timestamps=df_f["datetime"],
                variable=var,
                ventana_extremos=ventana,
            )
        )
        for var in _VARS_PRINCIPALES
    }

    return AnalisisCompletoResponse(
        fecha_inicio=df_f["datetime"].min().isoformat(),
        fecha_fin=df_f["datetime"].max().isoformat(),
        n_registros=len(df_f),
        **resultados,
    )


# ─── Solo regresión / tendencia (ligero) ─────────────────────────────────────

@router.get(
    "/regresion",
    summary="Regresión lineal y tendencia de todas las variables",
    description="""
Devuelve solo la **regresión lineal** (pendiente, R², tendencia, predicción a 1h)
para todas las variables en el rango indicado.

Respuesta mucho más ligera que `/analisis/completo` — ideal para tarjetas
de tendencia en el dashboard.
""",
)
def get_regresion(
    fecha_inicio: Optional[date] = Query(None, description="Inicio del rango (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fin del rango (YYYY-MM-DD)"),
) -> dict:

    df   = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin)

    if df_f.empty:
        raise HTTPException(status_code=404, detail="No hay datos en el rango indicado.")

    resultado: dict = {
        "fecha_inicio": df_f["datetime"].min().isoformat(),
        "fecha_fin":    df_f["datetime"].max().isoformat(),
        "n_registros":  len(df_f),
        "variables":    {},
    }

    for var in NUMERIC_COLS:
        if var not in df_f.columns:
            continue
        reg = regresion_lineal(df_f[var], df_f["datetime"])
        resultado["variables"][var] = RegresionLineal(**reg).model_dump()

    return resultado


# ─── Helper de conversión ────────────────────────────────────────────────────

def _dict_to_response(d: dict) -> AnalisisVariableResponse:
    """Convierte el dict devuelto por analisis_completo a schema Pydantic."""
    from app.schemas import PuntoDerivada, PuntoCritico, ExtremoGlobal

    derivada = [PuntoDerivada(**p) for p in d["derivada"]]

    puntos_criticos = [PuntoCritico(**p) for p in d["puntos_criticos"]]

    ext_raw = d["extremos"]
    extremos = ExtremosResult(
        maximo_global=ExtremoGlobal(**ext_raw["maximo_global"]) if ext_raw.get("maximo_global") else None,
        minimo_global=ExtremoGlobal(**ext_raw["minimo_global"]) if ext_raw.get("minimo_global") else None,
        maximos_locales=[ExtremoGlobal(**e) for e in ext_raw.get("maximos_locales", [])],
        minimos_locales=[ExtremoGlobal(**e) for e in ext_raw.get("minimos_locales", [])],
    )

    regresion = RegresionLineal(**d["regresion"])

    return AnalisisVariableResponse(
        variable=d["variable"],
        n_registros=d["n_registros"],
        derivada=derivada,
        puntos_criticos=puntos_criticos,
        extremos=extremos,
        regresion=regresion,
    )
