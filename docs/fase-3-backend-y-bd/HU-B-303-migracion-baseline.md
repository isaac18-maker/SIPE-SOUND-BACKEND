# HU-B-303 · Crear la migración *baseline* del esquema actual

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-302 |
| Rama | `hu/HU-B-303-baseline` |

## Historia
**Como** equipo
**quiero** que la base existente quede registrada como la revisión `0001`
**para** que todas las migraciones futuras partan de un punto conocido y un entorno nuevo pueda recrearse desde cero.

## Alcance
**Incluye**
- `migrations/versions/<fecha>-0001_baseline_esquema_supabase.py` que **crea** todo el esquema `public` del inventario: tablas, CHECK, FK con su `ON DELETE` actual, índices, función `handle_new_user`, trigger `on_auth_user_created`, `enable row level security` y políticas RLS (con `op.execute`).
- `downgrade()` que elimina lo anterior (marcado `# destructivo-aprobado: HU-B-303`, ya que solo aplica a entornos nuevos).
- Procedimiento de **stamp** para la base existente (no se ejecuta `upgrade` sobre ella).

**No incluye**: ningún cambio sobre el esquema actual.

## Prompt de ejecución
```text
Ejecuta HU-B-303 en SIPE-SOUND-BACKEND.
- Genera la revisión con --rev-id 0001. Escribe el upgrade a mano a partir de
  db/legacy/schema_real_*.sql (no confíes solo en autogenerate: no ve funciones,
  triggers ni políticas).
- Funciones, triggers y políticas con op.execute y su reverso en downgrade.
- La base de Supabase existente NO se migra: se marca con `alembic stamp 0001`.
- Valida en una base local vacía (Docker postgres:15 con un esquema auth y una
  tabla auth.users mínima) que upgrade/downgrade/upgrade funcionan y que
  `alembic check` no reporta diferencias con los modelos de HU-B-301.
```

## Pasos
1. Levantar Postgres local con `auth.users` mínimo:
   ```bash
   docker run -d --name sipe-pg -e POSTGRES_PASSWORD=local -p 54329:5432 postgres:15
   psql "postgresql://postgres:local@localhost:54329/postgres" -c "create schema auth; create table auth.users(id uuid primary key, email text, raw_user_meta_data jsonb); create role authenticated; create role anon;"
   ```
   (Supabase define `auth.uid()`; crear una función stub `auth.uid()` que devuelva `null::uuid` para que las políticas compilen.)
2. Escribir `0001` a mano.
3. `upgrade` → `downgrade base` → `upgrade` en local.
4. `alembic check` → sin diferencias.
5. En Supabase (staging primero): `pg_dump` de respaldo y `alembic stamp 0001`.

## Criterios de aceptación
```gherkin
Escenario: Entorno nuevo reproducible
  Dado una base PostgreSQL vacía con el stub de auth
  Cuando ejecuto alembic upgrade head
  Entonces obtengo el mismo esquema public que el dump real

Escenario: Base existente sin cambios
  Dado la base de Supabase actual
  Cuando ejecuto alembic stamp 0001
  Entonces alembic current muestra 0001 y ningún objeto fue modificado
```

## Verificación manual
```bash
uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
uv run alembic check
pg_dump --schema-only --schema=public <local> | diff - db/legacy/schema_real_*.sql   # solo diferencias cosméticas
```

## Definición de hecho específica
- [ ] `check_migrations.py` en verde.
- [ ] Respaldo de Supabase tomado antes del `stamp` (fecha anotada en el PR).
