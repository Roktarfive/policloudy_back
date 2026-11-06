"""GET /temperatura — Temperatura, sensación térmica e índice de calor."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import TemperaturaResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/temperatura", tags=["Temperatura"])


@router.get("", response_model=TemperaturaResponse, summary="Temperatura, sensación e índice de calor")
def get_temperatura(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
) -> TemperaturaResponse:
    """
    Devuelve temperatura (°C), temperatura mínima de sensación (°C)
    e índice de calor (°C) filtrados por rango de fechas y/o IDs.
    """
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)
    return TemperaturaResponse(
        total=len(df_f),
        datos=df_to_records(df_f, ["temperatura", "temp_sensacion_min", "indice_calor"]),
    )
