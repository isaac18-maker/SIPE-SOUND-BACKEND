# 05 · Contrato de base de datos y migraciones (Alembic)

## 1. Principios

1. **El esquema vive en el código.** Ningún cambio de estructura se hace desde el SQL Editor de Supabase. Todo pasa por una revisión en `migrations/versions/`.
2. **Historia lineal.** Siempre una sola `head`. Si hay dos, se resuelve con `alembic merge` en un PR propio.
3. **Toda revisión es reversible** (`downgrade()` real). Si no es posible, `downgrade()` lanza `NotImplementedError("motivo")` y el PR lo justifica.
4. **Esquema y datos separados.** Una revisión cambia estructura **o** migra datos, no ambas.
5. **Migraciones inmutables** una vez en `main`.

## 2. Convenciones de nombres

| Objeto | Convención | Ejemplo |
|---|---|---|
| Tabla | plural, `snake_case` | `intentos_evaluacion` |
| PK | `id` | `id serial` / `id uuid` |
| FK | `<entidad_singular>_id` | `curso_id`, `estudiante_id` |
| Fechas | `creado_en`, `actualizado_en`, `archivado_en` | `timestamptz` |
| Booleanos | `es_*`, `tiene_*` | `es_publicado` |
| Enum lógicos | `text` + `CHECK` (no `ENUM` nativo, más fácil de migrar) | `estado in ('borrador','publicado','archivado')` |

`MetaData(naming_convention=...)` obligatorio en `app/models/base.py`:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

## 3. Estructura de migraciones

```
alembic.ini
migrations/
├── env.py               # protecciones (sección 5)
├── script.py.mako       # plantilla con cabecera HU y marca destructiva
├── README.md            # comandos del día a día
└── versions/
    ├── 2026_10_28_0900-0001_baseline_esquema_supabase.py
    ├── 2026_10_29_1000-0002_profiles_rol.py
    └── ...
```

`alembic.ini`:

```ini
[alembic]
script_location = migrations
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
truncate_slug_length = 40
# la URL NO va aquí: env.py la lee de DATABASE_URL_MIGRATIONS
```

Identificadores de revisión **secuenciales legibles**: `alembic revision -m "..." --rev-id 0002`.

## 4. Política de borrado (ON DELETE)

| Padre → Hijo | ON DELETE | Por qué |
|---|---|---|
| `auth.users` → `profiles` | CASCADE | Si Supabase elimina la cuenta, el perfil no tiene sentido. |
| `profiles` → `inscripciones` | CASCADE | Datos del estudiante. |
| `profiles` → `progreso_lecciones`, `progreso_ejercicios` | CASCADE | Datos del estudiante (derecho de supresión). |
| `profiles` → `intentos_evaluacion` | CASCADE | Datos del estudiante. |
| `profiles` → `retroalimentaciones.estudiante_id` | CASCADE | Datos del estudiante. |
| `profiles` → `retroalimentaciones.docente_id` | SET NULL | El comentario sigue siendo útil para el estudiante. |
| `profiles` (docente) → `cursos.docente_id` | **RESTRICT** | Un curso no puede quedar huérfano: primero se reasigna. |
| `profiles` → `lecciones.autor_id`, `ejercicios.autor_id`, `evaluaciones.autor_id` | SET NULL | El contenido sobrevive a su autor. |
| `cursos` → `inscripciones`, `curso_bloques`, `retroalimentaciones` | CASCADE | Partes del curso. |
| `cursos` → `evaluaciones` (de curso) | CASCADE | Partes del curso. |
| `bloques` → `lecciones` | CASCADE | Una lección pertenece a un bloque. |
| `bloques` → `curso_bloques` | CASCADE | Tabla puente. |
| `bloques` → `evaluaciones` (de bloque) | CASCADE | Evaluación de cierre del bloque. |
| `lecciones` → `ejercicios` | SET NULL | El ejercicio puede existir suelto en la biblioteca. |
| `lecciones` → `progreso_lecciones` | CASCADE | Sin lección no hay progreso. |
| `lecciones` ↔ `acordes` (`leccion_acordes`) | CASCADE ambos lados | Tabla puente. |
| `ejercicios` → `progreso_ejercicios` | CASCADE | Sin ejercicio no hay progreso. |
| `evaluaciones` → `preguntas_evaluacion`, `intentos_evaluacion` | CASCADE | Partes de la evaluación. |

### Regla de negocio sobre la cascada ("cuando se dé el caso")

La cascada protege la **integridad**; la **aplicación** protege los **datos**:

- `DELETE` de contenido (`bloques`, `lecciones`, `ejercicios`, `evaluaciones`) **sin** progreso ni intentos → borrado físico (cascada).
- `DELETE` de contenido **con** progreso o intentos → `409 CONFLICTO` con `sugerencia: "archivar"`. El docente archiva (`estado = 'archivado'`, `archivado_en = now()`).
- `DELETE` de `cursos` desde el panel → siempre *soft delete* (`archivado_en`). El borrado físico solo lo hace un admin.
- Toda FK lleva **índice** en la columna hija.

## 5. Sistema de protección de Alembic

Se implementa en HU-B-302. Cada punto es obligatorio.

| # | Protección | Implementación |
|---|---|---|
| P1 | **No tocar esquemas de Supabase** (`auth`, `storage`, `realtime`, `extensions`, `graphql`, `vault`, `supabase_*`). Sin esto, `--autogenerate` intenta **borrar** sus tablas. | `include_name` en `env.py`: solo `schema in (None, "public")`; `include_schemas=False`. |
| P2 | **Bloqueo de operaciones destructivas en autogenerate.** | `process_revision_directives` recorre las operaciones; si encuentra `DropTable`, `DropColumn`, `DropConstraint` o cambio de tipo, aborta salvo `-x allow_destructive=true`. |
| P3 | **Marca de aprobación en el archivo.** | `scripts/check_migrations.py` falla si una revisión contiene `op.drop_*`, `op.execute("DELETE…/TRUNCATE…/DROP…")` sin el comentario `# destructivo-aprobado: HU-B-XXX`. Se ejecuta en CI y pre-commit. |
| P4 | **Confirmación explícita en producción.** | Si `APP_ENV=production`, `env.py` exige `-x confirmar=production`; si no, aborta antes de conectar. |
| P5 | **Timeouts** para no bloquear tablas en horas de clase. | Al inicio de cada transacción: `SET lock_timeout = '5s'; SET statement_timeout = '60s';` |
| P6 | **Una transacción por revisión.** | `context.configure(transaction_per_migration=True)`. |
| P7 | **Detección de tipos y defaults.** | `compare_type=True`, `compare_server_default=True`. |
| P8 | **Conexión correcta.** | `DATABASE_URL_MIGRATIONS` apunta a la conexión **directa** (puerto 5432), nunca al *pooler* en modo transacción (6543), que rompe DDL y *prepared statements*. |
| P9 | **Una sola head.** | `check_migrations.py` verifica `alembic heads` = 1. |
| P10 | **Respaldo previo en producción.** | Procedimiento documentado: `pg_dump --schema=public -Fc` antes de `upgrade`, y revisión del SQL con `alembic upgrade head --sql`. |
| P11 | **Objetos que autogenerate no ve** (funciones, triggers, políticas RLS, extensiones). | Se escriben a mano con `op.execute()` y su reverso en `downgrade()`. |

## 6. Plantilla `script.py.mako` (cabecera obligatoria)

```python
"""${message}

HU: HU-B-XXX
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
Tipo: esquema | datos
Destructiva: no   # si es "si", agregar: # destructivo-aprobado: HU-B-XXX
"""
```

## 7. Flujo del día a día

```bash
# 1. Cambiar el modelo en app/models/
# 2. Generar la revisión
uv run alembic revision --autogenerate -m "agregar estado a lecciones" --rev-id 0007
# 3. LEER y ajustar el archivo generado (autogenerate no es infalible)
# 4. Validar
uv run python scripts/check_migrations.py
# 5. Aplicar y revertir en local (prueba de reversibilidad)
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# 6. Verificar que el modelo y la BD no difieren
uv run alembic check
```

## 8. Datos semilla

- `scripts/seed_dev.py` solo corre si `APP_ENV=local`.
- Los datos de catálogo que **deben** existir en producción (p. ej. bloques iniciales) se cargan con una revisión de **datos** idempotente (`INSERT … ON CONFLICT DO NOTHING`).
