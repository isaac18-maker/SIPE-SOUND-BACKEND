# 07 · Definición de hecho (DoD) y flujo Git

## DoD general — aplica a TODA HU del backend

- [ ] Todos los criterios de aceptación verificados y evidenciados en el PR.
- [ ] `uv run ruff check .` sin errores.
- [ ] `uv run ruff format --check .` sin cambios pendientes.
- [ ] Ningún archivo nuevo rompe la regla de dependencia de capas.
- [ ] Ninguna función nueva supera complejidad cognitiva 15 (Sonar S3776).
- [ ] Sin `print`, sin código comentado, sin `except Exception` silencioso.
- [ ] Sin secretos; `.env.example` actualizado si se añadieron variables.
- [ ] Si se tocó el esquema: revisión Alembic creada, `check_migrations.py` en verde, `upgrade → downgrade → upgrade` probado en local, `alembic check` sin diferencias.
- [ ] Si cambió un contrato (API o BD): documento actualizado **en el mismo PR** y, si afecta al frontend, PR enlazado en `SIPE-SOUND-FULLSTACK`.
- [ ] Análisis SonarQube (o SonarLint en el IDE) sin *issues* nuevos de severidad *Blocker*/*Critical*.

## Ramas

| Rama | Uso |
|---|---|
| `main` | Producción. Protegida: solo PR con 1 aprobación. |
| `develop` | Integración de la fase en curso. |
| `hu/HU-B-XXX-slug` | Trabajo de una HU. Sale de `develop` y vuelve a `develop`. |
| `hotfix/descripcion` | Correcciones urgentes desde `main`. |

## Orden de merge entre repositorios

Cuando una HU de backend y una de frontend dependen entre sí (p. ej. HU-B-312 ↔ HU-F-306):

1. Se mergea primero el **backend** manteniendo compatibilidad hacia atrás.
2. Luego el **frontend**.
3. Por último una HU de limpieza retira la compatibilidad.

## Pipeline mínimo (CI) — sin pruebas en esta etapa

```yaml
# .github/workflows/calidad.yml (referencia)
steps:
  - uv sync --frozen
  - uv run ruff check .
  - uv run ruff format --check .
  - uv run python scripts/check_migrations.py
  - sonar-scanner   # Quality Gate sin condición de cobertura
```
