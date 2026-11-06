"""GET /radiacion — Radiación solar, índice UV y dosis UV."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import RadiacionResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/radiacion", tags=["Radiación Solar"])


@router.get("", response_model=RadiacionResponse, summary="Radiación solar, índice UV y dosis UV")
def get_radiacion(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
) -> RadiacionResponse:
    """
    Devuelve los registros de radiación solar (W/m²), índice UV
    y dosis de UV (MEDs) filtrados.
    """
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)
    return RadiacionResponse(
        total=len(df_f),
        datos=df_to_records(df_f, ["radiacion_solar", "indice_uv", "dosis_uv"]),
    )
