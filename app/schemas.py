"""
schemas.py
----------
Modelos Pydantic para las respuestas de la API.
Refleja las variables reales del CSV Davis Vantage Pro2.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ─── Upload CSV ───────────────────────────────────────────────────────────────

class CoberturaPct(BaseModel):
    """Porcentaje de celdas con datos válidos por variable."""
    barometro:             Optional[float] = None
    temperatura:           Optional[float] = None
    humedad:               Optional[float] = None
    viento_velocidad:      Optional[float] = None
    temp_sensacion_min:    Optional[float] = None
    indice_calor:          Optional[float] = None
    et:                    Optional[float] = None
    lluvia:                Optional[float] = None
    lluvia_intensidad_max: Optional[float] = None
    radiacion_solar:       Optional[float] = None
    indice_uv:             Optional[float] = None
    dosis_uv:              Optional[float] = None


class UploadResponse(BaseModel):
    mensaje:            str
    nombre_archivo:     str
    filas_totales:      int
    filas_validas:      int
    filas_descartadas:  int
    fecha_inicio:       str
    fecha_fin:          str
    cobertura_pct:      CoberturaPct


class DatasetStatusResponse(BaseModel):
    hay_datos:      bool
    nombre_archivo: Optional[str] = None
    filas_validas:  Optional[int] = None
    fecha_inicio:   Optional[str] = None
    fecha_fin:      Optional[str] = None


# ─── Registro base (todas las variables) ─────────────────────────────────────

class RegistroCompleto(BaseModel):
    """Fila completa con todas las variables ambientales."""
    model_config = ConfigDict(populate_by_name=True)

    id:                    int
    datetime:              datetime
    barometro:             Optional[float] = None
    temperatura:           Optional[float] = None
    humedad:               Optional[float] = None
    viento_velocidad:      Optional[float] = None
    temp_sensacion_min:    Optional[float] = None
    indice_calor:          Optional[float] = None
    et:                    Optional[float] = None
    lluvia:                Optional[float] = None
    lluvia_intensidad_max: Optional[float] = None
    radiacion_solar:       Optional[float] = None
    indice_uv:             Optional[float] = None
    dosis_uv:              Optional[float] = None


# ─── Temperatura ──────────────────────────────────────────────────────────────

class TemperaturaRecord(BaseModel):
    id:                 int
    datetime:           datetime
    temperatura:        Optional[float] = None
    temp_sensacion_min: Optional[float] = None
    indice_calor:       Optional[float] = None


class TemperaturaResponse(BaseModel):
    total: int
    datos: list[TemperaturaRecord]


# ─── Humedad ──────────────────────────────────────────────────────────────────

class HumedadRecord(BaseModel):
    id:       int
    datetime: datetime
    humedad:  Optional[float] = None


class HumedadResponse(BaseModel):
    total: int
    datos: list[HumedadRecord]


# ─── Viento ───────────────────────────────────────────────────────────────────

class VientoRecord(BaseModel):
    id:               int
    datetime:         datetime
    viento_velocidad: Optional[float] = None


class VientoResponse(BaseModel):
    total: int
    datos: list[VientoRecord]


# ─── Lluvia ───────────────────────────────────────────────────────────────────

class LluviaRecord(BaseModel):
    id:                    int
    datetime:              datetime
    lluvia:                Optional[float] = None
    lluvia_intensidad_max: Optional[float] = None
    et:                    Optional[float] = None


class LluviaResponse(BaseModel):
    total:        int
    acumulado_mm: Optional[float] = None
    datos:        list[LluviaRecord]


# ─── Radiación Solar ──────────────────────────────────────────────────────────

class RadiacionRecord(BaseModel):
    id:             int
    datetime:       datetime
    radiacion_solar: Optional[float] = None
    indice_uv:      Optional[float] = None
    dosis_uv:       Optional[float] = None


class RadiacionResponse(BaseModel):
    total: int
    datos: list[RadiacionRecord]


# ─── Barómetro ────────────────────────────────────────────────────────────────

class BarometroRecord(BaseModel):
    id:        int
    datetime:  datetime
    barometro: Optional[float] = None


class BarometroResponse(BaseModel):
    total: int
    datos: list[BarometroRecord]


# ─── Estadísticas por variable ────────────────────────────────────────────────

class EstadisticaVariable(BaseModel):
    promedio: Optional[float] = None
    maximo:   Optional[float] = None
    minimo:   Optional[float] = None
    moda:     Optional[float] = None


# ─── Resumen Diario ───────────────────────────────────────────────────────────

class ResumenDiarioResponse(BaseModel):
    fecha:                 str
    total_registros:       int
    barometro:             EstadisticaVariable
    temperatura:           EstadisticaVariable
    humedad:               EstadisticaVariable
    viento_velocidad:      EstadisticaVariable
    temp_sensacion_min:    EstadisticaVariable
    indice_calor:          EstadisticaVariable
    lluvia:                EstadisticaVariable
    lluvia_intensidad_max: EstadisticaVariable
    et:                    EstadisticaVariable
    radiacion_solar:       EstadisticaVariable
    indice_uv:             EstadisticaVariable
    dosis_uv:              EstadisticaVariable


# ─── Resumen Global ───────────────────────────────────────────────────────────

class ResumenGlobalResponse(BaseModel):
    fecha_inicio:          str
    fecha_fin:             str
    total_registros:       int
    barometro:             EstadisticaVariable
    temperatura:           EstadisticaVariable
    humedad:               EstadisticaVariable
    viento_velocidad:      EstadisticaVariable
    temp_sensacion_min:    EstadisticaVariable
    indice_calor:          EstadisticaVariable
    lluvia:                EstadisticaVariable
    lluvia_intensidad_max: EstadisticaVariable
    et:                    EstadisticaVariable
    radiacion_solar:       EstadisticaVariable
    indice_uv:             EstadisticaVariable
    dosis_uv:              EstadisticaVariable
