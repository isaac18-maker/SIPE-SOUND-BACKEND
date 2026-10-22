# HU-B-302 · Inicializar Alembic con el sistema de protección

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-301 |
| Rama | `hu/HU-B-302-alembic` |

## Historia
**Como** responsable de la base de datos
**quiero** que todo cambio de esquema pase por migraciones versionadas con salvaguardas
**para** que nadie borre por accidente tablas de Supabase o datos de estudiantes.

## Contexto
Hoy el esquema se modifica pegando SQL en Supabase. No hay historial, no hay forma de revertir, y un `alembic --autogenerate` ingenuo intentaría **eliminar** las tablas de `auth`, `storage` y `realtime` porque no existen en los modelos.

## Alcance
**Incluye** las protecciones **P1–P11** de [`05-contrato-base-datos.md`](../fase-1-contrato/05-contrato-base-datos.md#5-sistema-de-protección-de-alembic):
- `alembic.ini` (sin URL, con `file_template`).
- `migrations/env.py`, `migrations/script.py.mako`, `migrations/README.md`, `migrations/versions/` (vacía con `.gitkeep`).
- `scripts/check_migrations.py`.
- Hook de *pre-commit* (opcional) y paso en CI.

**No incluye**: la revisión *baseline* (HU-B-303).

## Prompt de ejecución
```text
Ejecuta HU-B-302 en SIPE-SOUND-BACKEND.
1) uv add alembic. Ejecuta `uv run alembic init migrations` y adapta los archivos.
2) env.py debe:
   - leer la URL de get_settings().database_url_migrations (nunca de alembic.ini);
   - target_metadata = Base.metadata (importando app.models para registrar todo);
   - include_name: aceptar solo type_=="schema" con name in (None,"public");
     para tablas, ignorar las del esquema "auth";
   - compare_type=True, compare_server_default=True, transaction_per_migration=True;
   - ejecutar "SET lock_timeout='5s'" y "SET statement_timeout='60s'" al conectar;
   - si settings.app_env == "production" y context.get_x_argument(as_dictionary=True)
     .get("confirmar") != "production": abortar con mensaje claro ANTES de conectar;
   - process_revision_directives: si autogenerate produce DropTableOp, DropColumnOp,
     DropConstraintOp, DropIndexOp o AlterColumnOp con modify_type, y no se pasó
     -x allow_destructive=true, abortar listando las operaciones.
3) script.py.mako con la cabecera obligatoria del contrato (HU, Tipo, Destructiva).
4) scripts/check_migrations.py (sin dependencias externas, usa ast o regex) que falle si:
   - un archivo de versions/ contiene op.drop_ o un op.execute con DROP/TRUNCATE/DELETE
     sin la línea "# destructivo-aprobado: HU-" en el mismo archivo;
   - la cabecera no tiene "HU:";
   - downgrade() está vacío o solo tiene `pass`;
   - hay más de una head (usa alembic.script.ScriptDirectory).
5) migrations/README.md con el flujo del día a día del contrato.
Prueba cada protección con una revisión de ensayo que luego borras (no se commitea).
```

## Pasos
1. Instalar e inicializar.
2. Implementar `env.py` (las 11 protecciones).
3. Plantilla `.mako`.
4. `check_migrations.py` con códigos de salida (0 ok, 1 fallo) y mensajes en español.
5. Ensayos de cada protección (ver verificación).
6. Documentar.

## Criterios de aceptación
```gherkin
Escenario: Autogenerate no toca Supabase
  Dado una base sin revisiones
  Cuando ejecuto alembic revision --autogenerate
  Entonces el archivo generado no menciona tablas de auth, storage ni realtime

Escenario: Bloqueo destructivo en autogenerate
  Dado que eliminé una columna de un modelo
  Cuando ejecuto alembic revision --autogenerate
  Entonces el comando aborta listando "DropColumn"
  Y no se crea el archivo

Escenario: Marca de aprobación
  Dado una revisión con op.drop_column sin "# destructivo-aprobado"
  Cuando ejecuto scripts/check_migrations.py
  Entonces termina con código 1 indicando archivo y línea

Escenario: Producción requiere confirmación
  Dado APP_ENV=production
  Cuando ejecuto alembic upgrade head sin -x confirmar=production
  Entonces aborta sin abrir conexión
```

## Verificación manual
```bash
uv run alembic current                    # conecta y no falla
uv run python scripts/check_migrations.py # OK con versions/ vacía
APP_ENV=production uv run alembic upgrade head        # aborta
uv run alembic upgrade head --sql | head  # muestra SET lock_timeout
```

## Definición de hecho específica
- [ ] `alembic.ini` no contiene ninguna URL ni contraseña.
- [ ] Cada protección P1–P11 tiene una línea en el PR con cómo se comprobó.
