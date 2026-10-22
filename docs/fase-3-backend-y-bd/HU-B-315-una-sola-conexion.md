# HU-B-315 · Simplificar la configuración a una sola conexión (Session pooler)

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Should |
| Estimación | 3 puntos |
| Depende de | HU-B-305, HU-B-313 |
| Rama | `hu/HU-B-315-una-conexion` |
| Origen | Solicitud del equipo (2026-10-22): demasiadas variables de conexión |

## Historia
**Como** desarrollador que configura el backend
**quiero** una sola cadena de conexión a la base de datos
**para** no confundir variables ni depender de dos formas de acceso a los datos.

## Contexto
El `.env` tenía `DATABASE_URL` (app), `DATABASE_URL_MIGRATIONS` (Alembic), `DATA_BACKEND` (API de Supabase o SQL), `SUPABASE_ANON_KEY` (API REST) y `SUPABASE_JWKS_URL` / `SUPABASE_JWT_SECRET` (tokens). El único uso que quedaba de la API REST de Supabase era guardar el resultado de los quizzes por bloque.

## Decisión
- **Una sola conexión: el Session pooler de Supabase** (`…pooler.supabase.com:5432`). En modo sesión soporta DDL y *prepared statements*, así que sirve a la app y a Alembic, y funciona por IPv4. El *Transaction pooler* (6543) sigue prohibido para migraciones.
- **Todo el acceso a datos por SQL.** La autorización la aplica el backend con el usuario del JWT (el `usuario_id` nunca viene del cliente).
- **JWKS deducido** de `SUPABASE_URL` (`/auth/v1/.well-known/jwks.json`). Se retira el modo HS256: el proyecto firma con ES256.

## Alcance
**Incluye**
- `Settings`: solo `SUPABASE_URL` y `DATABASE_URL` (+ `APP_ENV`, `FLASK_DEBUG`, `LOG_LEVEL`, `CORS_ORIGINS`, `SQLALCHEMY_ECHO`).
- Progreso de bloques por SQL (`SqlProgresoBloquesRepository`).
- Retirar `DATA_BACKEND`, repositorios de Supabase, `supabase_client.py`, `supabase_rest.py` y las dependencias `supabase` y `requests` (adelanta parte de HU-B-312).
- Alembic y `scripts/inventariar_esquema.py` usan `DATABASE_URL`.
- Contrato de BD (P8), arquitectura y `.env.example` actualizados.

## Criterios de aceptación
```gherkin
Escenario: Configuracion minima
  Dado un .env con SUPABASE_URL y DATABASE_URL (Session pooler)
  Cuando arranco la app y ejecuto alembic current
  Entonces ambos funcionan

Escenario: Sin la API REST de Supabase
  Cuando busco supabase_client, supabase_rest o "import requests" en app/
  Entonces no hay resultados

Escenario: Comportamiento intacto
  Cuando consulto el catalogo, el progreso y el quiz
  Entonces las respuestas son iguales a las de antes del cambio
```
