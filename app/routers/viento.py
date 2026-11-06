"""GET /viento — Velocidad media del viento."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import VientoResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/viento", tags=["Viento"])


@router.get("", response_model=VientoResponse, summary="Velocidad media del viento")
def get_viento(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
) -> VientoResponse:
    """Devuelve los registros de velocidad media del viento (m/s) filtrados."""
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)
    return VientoResponse(total=len(df_f), datos=df_to_records(df_f, ["viento_velocidad"]))
