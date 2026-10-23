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

## Versión de la API

La API existe **solo** bajo `/api/v1` y todas las respuestas, de éxito o de
error, usan la estructura estándar (`statusCode`, `status`, `data`, `success`,
`message`, `errors`, `timestamp`, `meta`). El prefijo `/api` sin versión se
retiró en HU-B-319: cualquier ruta antigua responde 404 con esa misma estructura.
