"""GET /resumen-diario — Estadísticas de todas las variables para un día."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ResumenDiarioResponse
from app.utils import calc_estadistica, require_df

router = APIRouter(prefix="/resumen-diario", tags=["Resumen Diario"])


@router.get("", response_model=ResumenDiarioResponse, summary="Resumen estadístico diario")
def get_resumen_diario(
    fecha: date = Query(..., description="Fecha del día a resumir (YYYY-MM-DD)"),
) -> ResumenDiarioResponse:
    """
    Recibe una **fecha** y calcula en tiempo real para todos los registros
    de ese día: promedio, máximo, mínimo y moda de cada variable ambiental.

    Variables incluidas:
    - Barómetro (mm Hg)
    - Temperatura (°C), Sensación mínima (°C), Índice de calor (°C)
    - Humedad (%)
    - Velocidad del viento (m/s)
    - Lluvia (mm), Intensidad máxima (mm/h), ET (mm)
    - Radiación solar (W/m²), Índice UV, Dosis UV (MEDs)
    """
    df = require_df()
    df_day = df.loc[df["datetime"].dt.date == fecha]

    if df_day.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No hay registros para la fecha {fecha.isoformat()}.",
        )

    return ResumenDiarioResponse(
        fecha=fecha.isoformat(),
        total_registros=len(df_day),
        barometro=calc_estadistica(df_day["barometro"]),
        temperatura=calc_estadistica(df_day["temperatura"]),
        humedad=calc_estadistica(df_day["humedad"]),
        viento_velocidad=calc_estadistica(df_day["viento_velocidad"]),
        temp_sensacion_min=calc_estadistica(df_day["temp_sensacion_min"]),
        indice_calor=calc_estadistica(df_day["indice_calor"]),
        lluvia=calc_estadistica(df_day["lluvia"]),
        lluvia_intensidad_max=calc_estadistica(df_day["lluvia_intensidad_max"]),
        et=calc_estadistica(df_day["et"]),
        radiacion_solar=calc_estadistica(df_day["radiacion_solar"]),
        indice_uv=calc_estadistica(df_day["indice_uv"]),
        dosis_uv=calc_estadistica(df_day["dosis_uv"]),
    )
