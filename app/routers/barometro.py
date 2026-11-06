"""GET /barometro — Presión barométrica."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import BarometroResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/barometro", tags=["Barómetro"])


@router.get("", response_model=BarometroResponse, summary="Presión barométrica")
def get_barometro(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
) -> BarometroResponse:
    """Devuelve los registros de presión barométrica (mm Hg) filtrados."""
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)
    return BarometroResponse(total=len(df_f), datos=df_to_records(df_f, ["barometro"]))
