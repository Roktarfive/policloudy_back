"""GET /resumen-global — Estadísticas de todo el dataset en memoria."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import ResumenGlobalResponse
from app.utils import calc_estadistica, require_df

router = APIRouter(prefix="/resumen-global", tags=["Resumen Global"])


@router.get(
    "",
    response_model=ResumenGlobalResponse,
    summary="Estadísticas globales de todo el dataset",
)
def get_resumen_global() -> ResumenGlobalResponse:
    """
    Calcula en tiempo real el promedio, máximo, mínimo y moda de todas
    las variables ambientales sobre el dataset completo cargado en memoria.
    """
    df = require_df()

    return ResumenGlobalResponse(
        fecha_inicio=df["datetime"].min().isoformat(),
        fecha_fin=df["datetime"].max().isoformat(),
        total_registros=len(df),
        barometro=calc_estadistica(df["barometro"]),
        temperatura=calc_estadistica(df["temperatura"]),
        humedad=calc_estadistica(df["humedad"]),
        viento_velocidad=calc_estadistica(df["viento_velocidad"]),
        temp_sensacion_min=calc_estadistica(df["temp_sensacion_min"]),
        indice_calor=calc_estadistica(df["indice_calor"]),
        lluvia=calc_estadistica(df["lluvia"]),
        lluvia_intensidad_max=calc_estadistica(df["lluvia_intensidad_max"]),
        et=calc_estadistica(df["et"]),
        radiacion_solar=calc_estadistica(df["radiacion_solar"]),
        indice_uv=calc_estadistica(df["indice_uv"]),
        dosis_uv=calc_estadistica(df["dosis_uv"]),
    )
