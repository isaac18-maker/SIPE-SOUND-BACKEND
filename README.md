# SIPE-SOUND · Backend

API REST de SIPE-SOUND, plataforma web para aprender guitarra de forma autoguiada,
con contenido por niveles, seguimiento del progreso y panel docente.
El frontend vive en el repositorio `SIPE-SOUND-FULLSTACK`.

## Requisitos

- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/)

## Instalar uv

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Correr el backend

```bash
uv sync
uv run uvicorn src.main:app --reload                              # desarrollo ASGI: http://localhost:8000
uv run python run.py                                              # alternativa Flask: http://localhost:5000
uv run waitress-serve --listen=0.0.0.0:8000 --threads=8 wsgi:app  # produccion
```

El punto de entrada de Uvicorn adapta la aplicación Flask existente a ASGI; no
cambia el framework ni las rutas de la API.

## Documentación de la API

Con el backend en ejecución (`APP_ENV=local` o `staging`), abre Swagger UI en
`http://localhost:5000/docs/` (Flask) o `http://localhost:8000/docs/` (Uvicorn/waitress).
El esquema OpenAPI está en `/openapi.json`. Solo se documenta el contrato vigente
(`/api/v1`) y todas las respuestas usan la estructura `RespuestaEstandar`.
En producción Swagger está desactivado. Para las operaciones protegidas, usa
**Authorize** e ingresa el token JWT de Supabase.

## Instalación

```bash
uv sync
uv sync --group dev     # agrega herramientas de desarrollo como Ruff
cp .env.example .env   # completa SUPABASE_URL y DATABASE_URL (Session pooler)
# Valores para local y produccion: docs/configuracion-entornos.md
uv run uvicorn src.main:app --reload
```

## Calidad

```bash
uv run ruff check .
uv run ruff format --check .
```

## Documentación

- `AGENTS.md`: reglas para agentes de IA y personas.
- `docs/`: contrato (fase 1) e historias de usuario (fases 2 y 3).

## Transición a `/api/v1`

Durante la reestructuración conviven dos prefijos con los mismos endpoints:

| Prefijo | Respuesta exitosa | Respuesta de error | Estado |
|---|---|---|---|
| `/api/v1/...` | Estructura estándar (`statusCode`, `status`, `data`, `success`, `message`, `errors`, `timestamp`, `meta`) | La misma estructura, con `success: false` | Contrato vigente. Úsalo en todo desarrollo nuevo. |
| `/api/...` | payload sin envolver | `{"error": "<mensaje>"}` | Legado, solo para el frontend actual. Se elimina en HU-B-312. |

Cambios que ya aplican a ambos prefijos:

| Situación | Antes | Ahora |
|---|---|---|
| `GET /lecciones/{id}` inexistente | 500 | 404 |
| Error de Supabase | Texto crudo de PostgREST con su código | 500 con mensaje genérico; el detalle va al log |
| Ruta o método inexistente | HTML de Flask | JSON con mensaje en español |
