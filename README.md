# API Estación Meteorológica — Poliema v2

API REST construida con **FastAPI + Pandas** (Python 3.10+).  
El dashboard **sube el CSV** en tiempo real y la API lo valida, limpia y deja en memoria para consultas inmediatas. Sin base de datos, sin archivos en disco.

---

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py              ← FastAPI app, CORS, registro de routers
│   ├── data_store.py        ← Store en memoria + pipeline de limpieza CSV
│   ├── schemas.py           ← Todos los modelos Pydantic de request/response
│   ├── utils.py             ← require_df(), filter_df(), df_to_records(), calc_estadistica()
│   └── routers/
│       ├── upload.py        ← POST /upload-csv  |  GET /dataset/status
│       ├── temperatura.py   ← GET /temperatura
│       ├── humedad.py       ← GET /humedad
│       ├── radiacion.py     ← GET /radiacion
│       ├── lluvia.py        ← GET /lluvia
│       ├── viento.py        ← GET /viento
│       ├── resumen_diario.py← GET /resumen-diario
│       └── resumen_global.py← GET /resumen-global
├── requirements.txt
└── run.py
```

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
```

## Ejecución

```bash
python run.py
# Swagger UI → http://localhost:8000/docs
```

---

## Flujo de uso

```
Dashboard                          FastAPI
   │                                  │
   │── POST /upload-csv (CSV file) ──►│  valida columnas
   │                                  │  limpia celdas basura → NaN
   │◄── 200 {filas, fechas, cobertura}│  guarda DataFrame en memoria
   │                                  │
   │── GET /resumen-global ──────────►│
   │◄── estadísticas de todo el CSV ──│
   │                                  │
   │── GET /resumen-diario?fecha= ───►│
   │◄── promedio/max/min/moda del día ┤
   │                                  │
   │── GET /temperatura?fecha_inicio= ►
   │◄── lista de registros filtrados ──
```

---

## Endpoints

### `POST /upload-csv`
Sube y carga el CSV. Reemplaza cualquier dataset previo.

**Body:** `multipart/form-data`, campo `file` (.csv, máx 50 MB)

**Validaciones:**
- Extensión `.csv`
- Todas las columnas requeridas presentes
- Al menos una fila con fecha válida (`DD/MM/YYYY HH:MM`)
- Celdas con solo caracteres especiales → `null`

**Respuesta 200:**
```json
{
  "mensaje": "CSV 'datos.csv' cargado exitosamente.",
  "nombre_archivo": "datos.csv",
  "filas_totales": 2880,
  "filas_validas": 2875,
  "filas_descartadas": 5,
  "fecha_inicio": "2026-07-15T00:00:00",
  "fecha_fin": "2026-07-29T23:45:00",
  "cobertura_pct": {
    "temperatura": 99.8,
    "humedad": 100.0,
    "viento_velocidad": 98.5,
    "lluvia": 100.0,
    "radiacion_solar": 99.1,
    "indice_uv": 99.1,
    "barometro": 97.3
  }
}
```

**Errores:**
- `415` — No es un CSV
- `413` — Archivo mayor a 50 MB
- `422` — Columnas faltantes o sin fechas válidas

---

### `GET /dataset/status`
Estado del dataset actualmente en memoria.

```json
{
  "hay_datos": true,
  "nombre_archivo": "datos.csv",
  "filas_validas": 2875,
  "fecha_inicio": "2026-07-15T00:00:00",
  "fecha_fin": "2026-07-29T23:45:00"
}
```

---

### `GET /temperatura` · `/humedad` · `/radiacion` · `/viento`
Retorna los registros de esa variable.

**Parámetros comunes (todos opcionales):**
| Parámetro | Tipo | Descripción |
|---|---|---|
| `fecha_inicio` | `YYYY-MM-DD` | Inicio del rango |
| `fecha_fin` | `YYYY-MM-DD` | Fin del rango |
| `ids` | `int[]` | IDs específicos (repetible) |

**Error 503** si no hay dataset cargado.

---

### `GET /lluvia`
Igual que las anteriores más:

| Parámetro | Valores | Descripción |
|---|---|---|
| `acumulado` | `mensual` \| `semanal` \| `ninguno` | Suma la lluvia del rango |

---

### `GET /resumen-diario?fecha=YYYY-MM-DD`
Estadísticas calculadas en tiempo real para un día específico.

```json
{
  "fecha": "2026-07-15",
  "total_registros": 96,
  "temperatura":     { "promedio": 21.5, "maximo": 27.5, "minimo": 16.9, "moda": 17.8 },
  "humedad":         { "promedio": 70.2, "maximo": 83.0, "minimo": 55.0, "moda": 72.0 },
  "viento_velocidad":{ "promedio": 1.8,  "maximo": 3.6,  "minimo": 0.5,  "moda": 1.3  },
  "lluvia":          { "promedio": 0.07, "maximo": 1.2,  "minimo": 0.0,  "moda": 0.0  },
  "radiacion_solar": { "promedio": 312.0,"maximo": 850.0,"minimo": 0.0,  "moda": 0.0  },
  "indice_uv":       { "promedio": 3.1,  "maximo": 8.5,  "minimo": 0.0,  "moda": 0.0  },
  "barometro":       { "promedio": 757.5,"maximo": 758.5,"minimo": 756.9,"moda": 757.0 }
}
```

**Error 404** si no hay registros para esa fecha.

---

### `GET /resumen-global`
Estadísticas de todo el dataset en memoria (sin filtros de fecha).

---

## Integración Flutter BLoC

```
features/weather/
├── bloc/
│   ├── upload_bloc.dart      ← UploadBloc  (POST /upload-csv)
│   ├── upload_event.dart
│   ├── upload_state.dart
│   ├── weather_bloc.dart     ← WeatherBloc (GET /resumen-diario)
│   ├── weather_event.dart
│   └── weather_state.dart
└── data/
    ├── models/
    │   ├── upload_response_model.dart
    │   └── weather_summary_model.dart
    └── repositories/
        └── weather_repository.dart
```

### `pubspec.yaml`
```yaml
dependencies:
  flutter_bloc: ^8.1.5
  http: ^1.2.1
  file_picker: ^8.0.0   # para seleccionar el CSV en el dashboard
```

### Ejemplo de uso en el dashboard

```dart
// Proveedor de BLoCs
MultiBlocProvider(
  providers: [
    BlocProvider(create: (_) => UploadBloc(repository: repo)),
    BlocProvider(create: (_) => WeatherBloc(repository: repo)),
  ],
  child: const DashboardPage(),
);

// 1. Subir el CSV
final result = await FilePicker.platform.pickFiles(
  type: FileType.custom,
  allowedExtensions: ['csv'],
);
if (result != null) {
  context.read<UploadBloc>().add(
    UploadCsvEvent(file: File(result.files.single.path!)),
  );
}

// 2. Escuchar resultado del upload
BlocBuilder<UploadBloc, UploadState>(
  builder: (context, state) => switch (state) {
    UploadInitial()  => const Text('Selecciona un archivo CSV'),
    UploadLoading()  => const CircularProgressIndicator(),
    UploadSuccess(:final result) => Text(
        '✓ ${result.filasValidas} registros cargados\n'
        '${result.fechaInicio} → ${result.fechaFin}',
      ),
    UploadError(:final message) => Text('Error: $message', style: const TextStyle(color: Colors.red)),
  },
);

// 3. Consultar resumen del día
context.read<WeatherBloc>().add(
  const FetchDailySummaryEvent(fecha: '2026-07-15'),
);
```
