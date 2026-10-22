# HU-B-316 · Corregir los riesgos detectados en configuración, despliegue y base de datos

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD (seguridad y operación) |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-315 |
| Rama | `hu/HU-B-316-riesgos` |
| Origen | Hallazgos de HU-B-206, HU-B-304 y de la guía de configuración (2026-10-22) |

## Historia
**Como** responsable de la plataforma
**quiero** que una configuración equivocada no pueda dañar la base de datos ni exponer el servidor
**para** operar SIPE-SOUND con seguridad aunque alguien se equivoque al llenar el `.env`.

## Riesgos y correcciones

| # | Riesgo | Corrección |
|---|---|---|
| R1 | Un error de escritura en `APP_ENV` (`produccion`, `Production`) desactiva las protecciones sin avisar | `APP_ENV` solo acepta `local`, `staging`, `production` |
| R2 | `APP_ENV=local` con `DATABASE_URL` apuntando a una base remota (producción) | Alembic y `scripts/*` se bloquean hasta corregir `APP_ENV` |
| R3 | `FLASK_DEBUG=1` (depurador con ejecución de código) o `SQLALCHEMY_ECHO=1` (datos en logs) en producción | La configuración es inválida y la app no arranca |
| R4 | `CORS_ORIGINS=*` o con `/` final (no coincide con el origen) | `*` se rechaza; la `/` final se elimina |
| R5 | Sin servidor WSGI de producción | Dependencia `waitress` y comando documentado |
| R6 | Migraciones sin respaldo (no hay `pg_dump` 17 disponible) | `scripts/respaldar_datos.py`: exporta `public` a JSON en solo lectura |
| R7 | `anon`/`authenticated` tienen `TRUNCATE`, `TRIGGER`, `REFERENCES` en todas las tablas; RLS no controla `TRUNCATE` | Revisión que los revoca, también en los privilegios por defecto de tablas futuras |
| R8 | `lecciones.bloque_id` nulo; `respuesta_correcta` fuera del rango de opciones | `NOT NULL` y `CHECK` (datos actuales: 0 casos que incumplan) |

## Criterios de aceptación
```gherkin
Escenario: APP_ENV mal escrito
  Dado APP_ENV=produccion
  Cuando arranco la app o Alembic
  Entonces falla indicando los valores validos

Escenario: Base remota con APP_ENV=local
  Dado APP_ENV=local y DATABASE_URL hacia supabase.com
  Cuando ejecuto alembic upgrade head
  Entonces se bloquea sin conectarse y explica como corregirlo

Escenario: Depurador en produccion
  Dado APP_ENV=production y FLASK_DEBUG=1
  Cuando arranco la app
  Entonces no arranca

Escenario: TRUNCATE con la anon key
  Dado la revision aplicada
  Cuando el rol anon intenta TRUNCATE sobre cualquier tabla
  Entonces recibe permission denied
```
