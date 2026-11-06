"""
data_store.py
-------------
Store en memoria del DataFrame activo.

El dashboard sube el CSV → el endpoint /upload-csv lo parsea y
llama a set_df(). Todos los routers leen el dato con get_df().

Formato soportado: exportación de Davis Vantage Pro2 / WeatherLink
con cabeceras de metadata en las primeras filas.
"""
from __future__ import annotations

import io
import re
import unicodedata

import numpy as np
import pandas as pd

# ─── Configuración de columnas ────────────────────────────────────────────────

# Mapeo exacto del CSV (con typos reales) → nombre interno normalizado
COLUMN_MAP: dict[str, str] = {
    "Date & Time":                              "datetime",
    # Barómetro
    "Barómetro - mm Hg":                        "barometro",
    "Bar�metro - mm Hg":                        "barometro",   # versión mojibake
    # Temperatura
    "Temp - °C":                                "temperatura",
    "Temp - &deg;C":                            "temperatura",
    # Humedad
    "Hum - %":                                  "humedad",
    # Viento (con typo en el CSV original: "Velocdad" sin 'i')
    "Velocdad del Viento Media - m/s":          "viento_velocidad",
    "Velocidad del Viento Media - m/s":         "viento_velocidad",
    # Temperatura de sensación mínima
    "Mínima de la Temperatura de Sensación - °C":    "temp_sensacion_min",
    "M&iacute;nima de la Temperatura de Sensaci&oacute;n - &deg;C": "temp_sensacion_min",
    "M�nima de la Temperatura de Sensaci�n - °C":   "temp_sensacion_min",
    "M�nima de la Temperatura de Sensaci�n - �C":   "temp_sensacion_min",
    # Índice de calor
    "Índice de calor - °C":                     "indice_calor",
    "�ndice de calor - °C":                     "indice_calor",
    "�ndice de calor - &deg;C":                 "indice_calor",
    "�ndice de calor - �C":                     "indice_calor",
    # ET
    "ET - mm":                                  "et",
    # Lluvia
    "Lluvia - mm":                              "lluvia",
    # Máxima intensidad de lluvia
    "Máxima Intensidad de Lluvia - mm":         "lluvia_intensidad_max",
    "M&aacute;xima Intensidad de Lluvia - mm":  "lluvia_intensidad_max",
    "M�xima Intensidad de Lluvia - mm":         "lluvia_intensidad_max",
    # Radiación solar (el CSV usa ^2, no ²)
    "Rad Solar - W/m^2":                        "radiacion_solar",
    "Rad Solar - W/m²":                         "radiacion_solar",
    # Índice UV
    "El Índice UV":                             "indice_uv",
    "El índice UV":                             "indice_uv",   # minúscula real del CSV
    "El �ndice UV":                             "indice_uv",
    "El &Iacute;ndice UV":                      "indice_uv",
    "Índice UV":                                "indice_uv",
    "�ndice UV":                                "indice_uv",
    # Dosis UV
    "Dosis de UV - MEDs":                       "dosis_uv",
}

# Nombre de la columna de fecha en el CSV
_DATE_COL = "Date & Time"

# Columnas numéricas (todo salvo datetime)
NUMERIC_COLS: list[str] = [
    "barometro",
    "temperatura",
    "humedad",
    "viento_velocidad",
    "temp_sensacion_min",
    "indice_calor",
    "et",
    "lluvia",
    "lluvia_intensidad_max",
    "radiacion_solar",
    "indice_uv",
    "dosis_uv",
]

# Columnas requeridas (nombres internos) que DEBEN aparecer en el CSV
REQUIRED_INTERNAL: list[str] = [
    "datetime",
    "barometro",
    "temperatura",
    "humedad",
    "viento_velocidad",
    "lluvia",
    "radiacion_solar",
    "indice_uv",
]

# Patrón que detecta celdas "basura": solo caracteres especiales / espacios / guiones
_GARBAGE_RE = re.compile(r"^[\s\-\*\?#@!\+~]+$")

# Codificaciones a intentar en orden
_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]


# ─── Store mutable ────────────────────────────────────────────────────────────

_df: pd.DataFrame | None = None
_upload_meta: dict = {}


def get_df() -> pd.DataFrame:
    if _df is None:
        raise ValueError(
            "No hay datos cargados. Sube un archivo CSV desde el dashboard "
            "usando POST /upload-csv."
        )
    return _df


def get_meta() -> dict:
    return dict(_upload_meta)


def set_df(df: pd.DataFrame, meta: dict | None = None) -> None:
    global _df, _upload_meta
    _df = df
    _upload_meta = meta or {}


def has_data() -> bool:
    return _df is not None


# ─── Clases de error ──────────────────────────────────────────────────────────

class CSVValidationError(Exception):
    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _clean_cell(val: object) -> object:
    """Celdas vacías o con solo caracteres basura → None."""
    if not isinstance(val, str):
        return val
    stripped = val.strip()
    if stripped == "" or _GARBAGE_RE.match(stripped):
        return None
    return stripped


def _normalize(name: str) -> str:
    """Normalización Unicode NFKC + strip para comparación flexible."""
    if not isinstance(name, str):
        return str(name)
    return unicodedata.normalize("NFKC", name.strip())


def _try_read_raw(content: bytes) -> tuple[pd.DataFrame, str]:
    """
    Lee el CSV de Davis WeatherLink (cp1252, sep=coma, comillas RFC).
    Las primeras filas tienen solo 1 celda (sin comas), lo que confunde
    la inferencia de columnas de pandas. Se lee con un número fijo de
    columnas dummy para evitar ese problema.
    """
    last_error: Exception | None = None

    # Contar el máximo de comas en cualquier línea para saber cuántas columnas hay
    def _max_cols(raw_bytes: bytes, enc: str) -> int:
        try:
            text = raw_bytes.decode(enc, errors="replace")
            return max((line.count(",") for line in text.splitlines() if line.strip()), default=0) + 1
        except Exception:
            return 20  # fallback conservador

    for enc in ["cp1252", "latin-1", "utf-8-sig", "utf-8"]:
        try:
            ncols = _max_cols(content, enc)
            col_names = list(range(ncols))

            df = pd.read_csv(
                io.BytesIO(content),
                dtype=str,
                encoding=enc,
                sep=",",
                engine="python",
                header=None,
                names=col_names,        # fuerza el número de columnas
                skip_blank_lines=False,
                on_bad_lines="skip",
            )
            if not df.empty:
                return df, enc
            last_error = ValueError(f"DataFrame vacío con {enc}")
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise CSVValidationError(
        "No se pudo leer el archivo CSV.",
        details=[f"Último error: {last_error}"],
    )


def _find_header_row(df: pd.DataFrame) -> int:
    """
    Busca la fila que contiene 'Date' y 'Time' en cualquier celda.
    En el CSV Davis las primeras filas son metadata de 1 sola columna,
    y la fila de encabezados tiene muchas columnas con 'Date & Time' en la primera.
    """
    for i, row in df.iterrows():
        for cell in row:
            if isinstance(cell, str) and "Date" in cell and "Time" in cell:
                return int(i)
    # Si no encontramos "Date & Time" exacto, buscar solo "Date"
    for i, row in df.iterrows():
        for cell in row:
            if isinstance(cell, str) and cell.strip().startswith("Date"):
                return int(i)
    raise CSVValidationError(
        "No se encontró la fila de encabezados con 'Date & Time'.",
        details=[
            "Primeras 6 filas del archivo: "
            + str(df.head(6).fillna("").values.tolist())
        ],
    )


# ─── Pipeline principal ───────────────────────────────────────────────────────

def parse_and_validate(content: bytes, filename: str = "archivo.csv") -> tuple[pd.DataFrame, dict]:
    """
    Parsea, valida y limpia el CSV ambiental de Davis Vantage Pro2.

    Returns
    -------
    df   : DataFrame limpio con índice 0-based y columnas normalizadas.
    meta : Metadata del dataset.

    Raises
    ------
    CSVValidationError si el archivo no es parseable o tiene formato incorrecto.
    """
    # 1. Leer todo sin cabecera para detectar filas de metadata
    raw_all, enc = _try_read_raw(content)

    if raw_all.empty:
        raise CSVValidationError(f"El archivo '{filename}' está vacío.")

    # 2. Encontrar la fila con los encabezados reales
    header_row = _find_header_row(raw_all)

    # 3. Releer el CSV con la fila de encabezados correcta
    try:
        raw = pd.read_csv(
            io.BytesIO(content),
            dtype=str,
            encoding=enc,
            sep=",",
            engine="python",
            header=header_row,
            skip_blank_lines=True,
            on_bad_lines="skip",
        )
    except Exception as exc:
        raise CSVValidationError(
            f"Error al releer el CSV con encabezado en fila {header_row}: {exc}",
            details=[str(exc)],
        ) from exc

    if raw.empty:
        raise CSVValidationError(f"El archivo '{filename}' no tiene filas de datos.")

    # 4. Limpiar nombres de columna: strip
    raw.columns = [str(c).strip() for c in raw.columns]

    # 5. Construir mapa de renombrado intentando:
    #    a) match exacto
    #    b) match normalizado NFKC (resuelve ², acentos, etc.)
    norm_col_map: dict[str, str] = {_normalize(k): v for k, v in COLUMN_MAP.items()}

    rename_map: dict[str, str] = {}
    matched_internal: set[str] = set()

    for csv_col in raw.columns:
        # a) Exacto
        if csv_col in COLUMN_MAP:
            rename_map[csv_col] = COLUMN_MAP[csv_col]
            matched_internal.add(COLUMN_MAP[csv_col])
            continue
        # b) Normalizado
        norm_csv = _normalize(csv_col)
        if norm_csv in norm_col_map:
            internal = norm_col_map[norm_csv]
            rename_map[csv_col] = internal
            matched_internal.add(internal)

    # 6. Verificar columnas requeridas
    missing = [c for c in REQUIRED_INTERNAL if c not in matched_internal]
    if missing:
        found = list(raw.columns)
        raise CSVValidationError(
            f"Faltan {len(missing)} columna(s) requerida(s) en el CSV.",
            details=[f"Falta: '{c}'" for c in missing]
            + [f"Columnas encontradas: {found}"],
        )

    # 7. Renombrar
    raw.rename(columns=rename_map, inplace=True)

    total_filas_raw = len(raw)

    # 8. Limpiar celdas basura (vectorizado)
    str_cols = raw.select_dtypes(include="object").columns.tolist()
    raw[str_cols] = raw[str_cols].apply(lambda col: col.map(_clean_cell))

    # 9. Parsear datetime  — formato: "15/7/26 12:00 AM"
    raw["datetime"] = pd.to_datetime(
        raw["datetime"],
        dayfirst=True,
        errors="coerce",
    )

    # 10. Convertir columnas numéricas → float64
    numeric_present = [c for c in NUMERIC_COLS if c in raw.columns]
    raw[numeric_present] = raw[numeric_present].apply(pd.to_numeric, errors="coerce")

    # 11. Añadir columnas opcionales faltantes como NaN
    for col in NUMERIC_COLS:
        if col not in raw.columns:
            raw[col] = np.nan

    # 12. Contar y descartar filas sin fecha válida
    invalid_rows = int(raw["datetime"].isna().sum())
    raw = raw.dropna(subset=["datetime"])

    if raw.empty:
        raise CSVValidationError(
            "Ninguna fila tiene una fecha/hora válida en 'Date & Time'.",
            details=["Formato esperado: DD/MM/YY HH:MM AM/PM  (ej: 15/7/26 12:00 AM)"],
        )

    # 13. Ordenar cronológicamente y resetear índice
    raw = raw.sort_values("datetime").reset_index(drop=True)

    # 14. Cobertura de datos por columna
    cobertura = {
        col: round(float(raw[col].notna().mean()) * 100, 1)
        for col in NUMERIC_COLS
        if col in raw.columns
    }

    meta = {
        "nombre_archivo":    filename,
        "filas_totales":     total_filas_raw,
        "filas_validas":     len(raw),
        "filas_descartadas": invalid_rows,
        "fecha_inicio":      raw["datetime"].min().isoformat(),
        "fecha_fin":         raw["datetime"].max().isoformat(),
        "cobertura_pct":     cobertura,
    }

    return raw, meta
