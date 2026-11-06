"""
main.py — Punto de entrada de la API FastAPI.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    upload,
    barometro,
    temperatura,
    humedad,
    viento,
    lluvia,
    radiacion,
    resumen_diario,
    resumen_global,
)

app = FastAPI(
    title="API Estación Meteorológica – Poliema",
    description=(
        "API REST para consulta de datos ambientales de la estación Davis Vantage Pro2. "
        "El dashboard sube el CSV con **POST /upload-csv** y luego consulta "
        "los datos con los endpoints GET. Construida con FastAPI + Pandas."
    ),
    version="2.1.0",
    contact={"name": "Poliema", "email": "contacto@poliema.edu"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Dataset management
app.include_router(upload.router)

# Variables ambientales
app.include_router(barometro.router)
app.include_router(temperatura.router)
app.include_router(humedad.router)
app.include_router(viento.router)
app.include_router(lluvia.router)
app.include_router(radiacion.router)

# Resúmenes estadísticos
app.include_router(resumen_diario.router)
app.include_router(resumen_global.router)


@app.get("/", tags=["Estado"], summary="Health-check")
def root() -> dict[str, str]:
    return {"estado": "ok", "version": "2.1.0", "docs": "/docs"}
