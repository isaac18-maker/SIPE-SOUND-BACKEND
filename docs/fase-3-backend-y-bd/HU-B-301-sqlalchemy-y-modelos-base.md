# HU-B-301 · Incorporar SQLAlchemy y los modelos base

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-203, HU-B-206 |
| Rama | `hu/HU-B-301-sqlalchemy` |

## Historia
**Como** desarrollador
**quiero** acceder a PostgreSQL mediante un ORM tipado con transacciones
**para** tener integridad referencial, consultas compuestas (panel docente) y migraciones versionadas.

## Contexto
Hoy los datos se leen con el cliente de Supabase (PostgREST). No hay transacciones ni joins tipados, y cada consulta compuesta del panel docente requeriría varias llamadas HTTP.

## Alcance
**Incluye**
- Dependencias: `sqlalchemy>=2.0`, `psycopg[binary]>=3.1`.
- `app/infrastructure/database.py`: `engine`, `SessionLocal`, `session_scope()` (context manager con commit/rollback).
- `app/models/base.py`: `Base(DeclarativeBase)` con `MetaData(naming_convention=...)` del contrato, `TimestampMixin` (`creado_en`, `actualizado_en`).
- Modelos que reflejan **exactamente** el inventario de HU-B-206 (sin cambios de esquema todavía): `Profile`, `Bloque`, `Leccion`, `Ejercicio`, `Acorde`, `Partitura`, `QuizPregunta`, `Progreso`.
- Tabla *stub* `auth.users` (solo `id`) para declarar la FK de `profiles`, **excluida** de Alembic.
- Repositorios SQLAlchemy de **lectura** para bloques, lecciones, ejercicios y acordes en `app/repositories/sqlalchemy/`, conmutables con los de Supabase.
- Variables `DATABASE_URL` (pooler, para la app) y `DATABASE_URL_MIGRATIONS` (directa 5432).

**No incluye**: Alembic (HU-B-302), cambios de esquema, escritura.

## Prompt de ejecución
```text
Ejecuta HU-B-301 en SIPE-SOUND-BACKEND.
- Instala sqlalchemy y psycopg[binary]. Usa el estilo 2.0 tipado (Mapped, mapped_column).
- Crea app/infrastructure/database.py y app/models/ como describe la HU. Los
  modelos deben reflejar db/legacy/INVENTARIO.md columna por columna (tipos,
  nullabilidad, defaults, CHECK y ON DELETE actuales). No inventes columnas.
- Para auth.users declara Table("users", metadata, Column("id", UUID, primary_key=True), schema="auth").
- Implementa repositorios de lectura en app/repositories/sqlalchemy/ que cumplan
  los mismos Protocol de app/repositories/base.py.
- Agrega en Settings: DATABASE_URL, DATABASE_URL_MIGRATIONS, DATA_BACKEND
  ("supabase" | "sql", por defecto "supabase"). El container elige la
  implementación según DATA_BACKEND.
- Si DATABASE_URL usa el pooler en modo transacción (puerto 6543), configura
  connect_args={"prepare_threshold": None} para psycopg.
- Las respuestas de los GET deben ser idénticas con DATA_BACKEND=supabase y =sql.
```

## Pasos
1. Dependencias y variables (`.env.example` con ejemplos falsos de ambas URL).
2. `database.py` con `pool_pre_ping=True`.
3. `models/base.py` y un archivo por modelo en `app/models/`.
4. Repositorios SQLAlchemy de lectura.
5. Conmutación por `DATA_BACKEND` en el container (demostración de DIP/LSP).
6. Comparar respuestas en ambos modos.

## Criterios de aceptación
```gherkin
Escenario: Intercambio de implementación
  Dado DATA_BACKEND=sql
  Cuando consulto GET /api/v1/lecciones
  Entonces la respuesta es idéntica a la obtenida con DATA_BACKEND=supabase

Escenario: Fidelidad del modelo
  Cuando comparo los modelos con db/legacy/INVENTARIO.md
  Entonces cada tabla, columna, FK y CHECK coincide
```

## Verificación manual
```bash
DATA_BACKEND=supabase uv run python run.py  # capturar salidas
DATA_BACKEND=sql uv run python run.py       # capturar salidas y diff
uv run python -c "from app.models.base import Base; import app.models; print(sorted(Base.metadata.tables))"
```

## Definición de hecho específica
- [ ] Ningún repositorio hace `commit()`.
- [ ] `session_scope()` hace rollback ante excepción y cierra la sesión siempre.
