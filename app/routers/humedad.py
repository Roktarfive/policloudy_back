"""GET /humedad — Humedad relativa."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import HumedadResponse
from app.utils import filter_df, df_to_records, require_df

router = APIRouter(prefix="/humedad", tags=["Humedad"])


@router.get("", response_model=HumedadResponse, summary="Humedad relativa")
def get_humedad(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin:    Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ids:          Optional[list[int]] = Query(None, description="IDs específicos de registros"),
) -> HumedadResponse:
    """Devuelve los registros de humedad relativa (%) filtrados."""
    df = require_df()
    df_f = filter_df(df, fecha_inicio, fecha_fin, ids)
    return HumedadResponse(total=len(df_f), datos=df_to_records(df_f, ["humedad"]))
