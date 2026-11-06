"""GET /lluvia — Precipitación, intensidad máxima y evapotranspiración."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Query

from app.schemas import LluviaResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/lluvia", tags=["Lluvia"])


@router.get("", response_model=LluviaResponse, summary="Precipitación, intensidad máxima y ET")
def get_lluvia(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
    acumulado:    Literal["mensual", "semanal", "ninguno"] = Query(
        "ninguno",
        description="Suma acumulada de lluvia dentro del rango: mensual | semanal | ninguno",
    ),
) -> LluviaResponse:
    """
    Devuelve registros de precipitación (mm), máxima intensidad de lluvia (mm/h)
    y evapotranspiración ET (mm).

    - `acumulado=mensual` o `semanal`: suma la lluvia del rango filtrado.
    - `acumulado=ninguno` (default): sin acumulado.
    """
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)

    acumulado_mm: float | None = None
    if acumulado != "ninguno" and not df_f.empty:
        acumulado_mm = round(float(df_f["lluvia"].sum(min_count=1)), 4)

    return LluviaResponse(
        total=len(df_f),
        acumulado_mm=acumulado_mm,
        datos=df_to_records(df_f, ["lluvia", "lluvia_intensidad_max", "et"]),
    )
