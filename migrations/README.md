# Migraciones (Alembic)

Reglas completas: [`docs/fase-1-contrato/05-contrato-base-datos.md`](../docs/fase-1-contrato/05-contrato-base-datos.md).
Todo cambio de esquema pasa por aquí. **Nunca** se modifica la base desde el SQL Editor de Supabase.

## Requisito
`DATABASE_URL_MIGRATIONS` en el `.env`: conexión **directa** de Supabase (puerto 5432).
Nunca el *transaction pooler* (6543): rompe el DDL.

## Día a día

```bash
# 1. Cambiar el modelo en app/models/
# 2. Generar la revisión (id secuencial legible)
uv run alembic revision --autogenerate -m "agregar estado a lecciones" --rev-id 0007
# 3. LEER el archivo generado y completar la cabecera: HU, Tipo, Destructiva
# 4. Validar
uv run python scripts/check_migrations.py
# 5. Probar reversibilidad en una base LOCAL
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# 6. Confirmar que modelo y base no difieren
uv run alembic check
```

## Protecciones activas

| # | Protección | Dónde |
|---|---|---|
| P1 | Solo se gestiona `public`; `auth`, `storage`, `realtime`… se ignoran | `env.py` (`incluir_nombre`, `incluir_objeto`) |
| P2 | Autogenerate aborta ante `DropTable`, `DropColumn`, `DropConstraint`, `DropIndex` o cambio de tipo, salvo `-x allow_destructive=true` | `env.py` (`bloquear_destructivas`) |
| P3 | En `upgrade()`, cada `op.drop_*` u `op.execute` con DROP/TRUNCATE/DELETE necesita `# destructivo-aprobado: HU-B-NNN` en la misma línea o en la anterior | `scripts/check_migrations.py` |
| P4 | Con `APP_ENV=production` se exige `-x confirmar=production` antes de abrir la conexión | `env.py` |
| P5 | `lock_timeout = 5s` y `statement_timeout = 60s` en la sesión | `env.py` |
| P6 | Una transacción por revisión | `env.py` |
| P7 | Se comparan tipos y defaults | `env.py` |
| P8 | La URL sale de `DATABASE_URL_MIGRATIONS`, nunca de `alembic.ini` | `env.py` |
| P9 | Una sola head | `scripts/check_migrations.py` |
| P10 | Respaldo y revisión del SQL antes de producción | Procedimiento abajo |
| P11 | Objetos que autogenerate no ve | Regla abajo |

Además, la cabecera de cada revisión debe tener `HU:` y `Tipo:`, y `downgrade()` no puede estar vacío.

## P10 · Antes de migrar producción

```bash
# 1. Respaldo del esquema y los datos de public (requiere pg_dump >= 17)
pg_dump "$DATABASE_URL_MIGRATIONS" --schema=public -Fc -f respaldo_$(date +%Y%m%d_%H%M).dump
pg_restore --list respaldo_*.dump | head      # el respaldo se puede leer

# 2. Revisar el SQL exacto que se ejecutará
uv run alembic upgrade head --sql > revisar.sql

# 3. Aplicar
APP_ENV=production uv run alembic -x confirmar=production upgrade head
```

## P11 · Objetos que autogenerate NO detecta

Se escriben a mano con `op.execute()` y su reverso en `downgrade()`:
funciones, triggers, políticas RLS, `grant`/`revoke`, extensiones.

**No se gestionan desde aquí** (son de Supabase): la función `public.rls_auto_enable()` y los
event triggers `ensure_rls`, `issue_*` y `pgrst_*`.
Por `ensure_rls`, **toda tabla nueva en `public` nace con RLS activo y sin políticas**: si el
frontend o la API REST de Supabase necesitan leerla, la revisión debe crear la política.

## Ver también
- Inventario del esquema heredado: [`db/legacy/INVENTARIO.md`](../db/legacy/INVENTARIO.md)
