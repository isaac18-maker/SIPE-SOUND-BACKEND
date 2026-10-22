# SIPE-SOUND · Backend

API REST de SIPE-SOUND, plataforma web para aprender guitarra de forma autoguiada,
con contenido por niveles, seguimiento del progreso y panel docente.
El frontend vive en el repositorio `SIPE-SOUND-FULLSTACK`.

## Requisitos

- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/)

## Instalación

```bash
uv sync
cp .env.example .env   # y completa SUPABASE_URL y SUPABASE_ANON_KEY
uv run python run.py   # http://localhost:5000
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
| `/api/v1/...` | `{"data": ...}` | `{"error": {"code", "message", "details"}}` | Contrato vigente. Úsalo en todo desarrollo nuevo. |
| `/api/...` | payload sin envolver | `{"error": "<mensaje>"}` | Legado, solo para el frontend actual. Se elimina en HU-B-312. |

Cambios que ya aplican a ambos prefijos:

| Situación | Antes | Ahora |
|---|---|---|
| `GET /lecciones/{id}` inexistente | 500 | 404 |
| Error de Supabase | Texto crudo de PostgREST con su código | 500 con mensaje genérico; el detalle va al log |
| Ruta o método inexistente | HTML de Flask | JSON con mensaje en español |
