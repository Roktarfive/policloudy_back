"""
POST /upload-csv       — Recibe, valida y carga el CSV desde el dashboard.
GET  /dataset/status   — Estado actual del dataset en memoria.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.data_store import (
    CSVValidationError,
    get_meta,
    has_data,
    parse_and_validate,
    set_df,
)
from app.schemas import CoberturaPct, DatasetStatusResponse, UploadResponse

router = APIRouter(tags=["Dataset"])

# Límite de tamaño: 50 MB
_MAX_SIZE_BYTES = 50 * 1024 * 1024



@router.post(
    "/upload-csv",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Subir archivo CSV de datos ambientales",
    description=(
        "Recibe un archivo CSV con los datos de la estación meteorológica, "
        "lo valida, limpia y lo deja disponible en memoria para todos los "
        "endpoints de consulta. **Reemplaza cualquier dataset previo.**\n\n"
        "### Columnas requeridas en el CSV\n"
        "| Columna | Unidad |\n"
        "|---|---|\n"
        "| Date & Time | DD/MM/YYYY HH:MM |\n"
        "| Temp - °C | °C |\n"
        "| Hum - % | % |\n"
        "| Velocidad del Viento Media - m/s | m/s |\n"
        "| Lluvia - mm | mm |\n"
        "| Rad Solar - W/m² | W/m² |\n"
        "| Índice UV | adimensional |\n"
        "| Barómetro - mm Hg | mm Hg |\n"
    ),
)
async def upload_csv(
    file: UploadFile = File(..., description="Archivo CSV con datos ambientales"),
) -> UploadResponse:
    # 1. Validar extensión del archivo (el content-type no es confiable)
    filename = file.filename or "archivo.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Solo se aceptan archivos .csv — recibido: '{filename}'",
        )

    # 2. Leer contenido con límite de tamaño
    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {_MAX_SIZE_BYTES // (1024*1024)} MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    # 3. Parsear y validar con Pandas
    try:
        df, meta = parse_and_validate(content, filename=filename)
    except CSVValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc), "detalles": exc.details},
        ) from exc

    # 4. Guardar en el store en memoria
    set_df(df, meta)

    return UploadResponse(
        mensaje=f"CSV '{filename}' cargado exitosamente.",
        nombre_archivo=meta["nombre_archivo"],
        filas_totales=meta["filas_totales"],
        filas_validas=meta["filas_validas"],
        filas_descartadas=meta["filas_descartadas"],
        fecha_inicio=meta["fecha_inicio"],
        fecha_fin=meta["fecha_fin"],
        cobertura_pct=CoberturaPct(**meta["cobertura_pct"]),
    )


@router.get(
    "/dataset/status",
    response_model=DatasetStatusResponse,
    summary="Estado del dataset en memoria",
    description="Informa si hay datos cargados y muestra su metadata básica.",
)
def dataset_status() -> DatasetStatusResponse:
    if not has_data():
        return DatasetStatusResponse(hay_datos=False)

    meta = get_meta()
    return DatasetStatusResponse(
        hay_datos=True,
        nombre_archivo=meta.get("nombre_archivo"),
        filas_validas=meta.get("filas_validas"),
        fecha_inicio=meta.get("fecha_inicio"),
        fecha_fin=meta.get("fecha_fin"),
    )
