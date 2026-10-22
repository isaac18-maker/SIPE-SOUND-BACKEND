# AGENTS.md · SIPE-SOUND Backend

Instrucciones para cualquier agente de IA que trabaje en este repositorio.

## Qué es esto
API REST (Flask + PostgreSQL/Supabase) de SIPE-SOUND, plataforma para aprender
guitarra de forma autoguiada, con seguimiento de progreso y panel docente.
Frontend en el repositorio hermano `SIPE-SOUND-FULLSTACK`.

## Antes de escribir código
1. Lee `docs/fase-1-contrato/` completo (contrato vinculante).
2. Lee la HU asignada en `docs/fase-2-reestructuracion/` o `docs/fase-3-backend-y-bd/`.
3. Si la HU contradice el contrato, gana el contrato: avisa.

## Reglas que no se negocian
- Una HU por rama y por PR. No salgas del alcance.
- Controladores (`app/api`) → servicios (`app/services`) → repositorios (`app/repositories`). Nunca al revés.
- Todo cambio de esquema es una revisión en `migrations/versions/`. Nunca SQL manual en Supabase.
- No edites migraciones ya mergeadas. No borres datos sin `# destructivo-aprobado: HU-B-XXX`.
- Nunca leas ni muestres `.env`. Variables nuevas → `.env.example`.
- Sin pruebas unitarias en esta etapa (decisión del equipo).
- Español en docs, comentarios, mensajes y commits.

## Comandos
```bash
uv sync                                   # instalar
uv run python run.py                      # servidor local :5000
uv run ruff check . && uv run ruff format --check .
uv run alembic upgrade head               # migraciones
uv run python scripts/check_migrations.py # guardia de migraciones
```
