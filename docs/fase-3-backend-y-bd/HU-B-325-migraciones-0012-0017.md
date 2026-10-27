# HU-B-325 · Poner la base al día con las migraciones 0012–0017

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must (bloqueante) |
| Estimación | 2 puntos |
| Depende de | HU-B-312, HU-B-319, HU-B-320, HU-B-321 (las migraciones), HU-B-302 (protecciones) |
| Rama | `docs/HU-B-325-migraciones` (operación; sin cambios de código) |
| Estado | **Ejecutada el 2026-10-23** |

## Historia
**Como** equipo
**quiero** que la base esté en la misma revisión que el código
**para** que la ruta, el progreso y las evaluaciones funcionen en lugar de responder 500.

## Contexto
El código esperaba la revisión `0017`, pero la base seguía en `0011`. Las tablas `evaluaciones`,
`preguntas_evaluacion` e `intentos_evaluacion` no existían, así que `GET /ruta`,
`GET /progreso/resumen` y `GET /progreso/actividad` respondían 500
(`relation "evaluaciones" does not exist`).

| Revisión | Contenido | Tipo |
|---|---|---|
| 0012 | Retira `duracion` (texto) de lecciones y ejercicios | Destructiva (aprobada en HU-B-319) |
| 0013 | Límites de longitud y rango | Restricciones |
| 0014 | Docentes preautorizados y triggers de alta y confirmación | Estructura |
| 0015 | `evaluaciones`, `preguntas_evaluacion`, `intentos_evaluacion` | Estructura |
| 0016 | Copia quizzes y resultados a evaluaciones e intentos | Datos |
| 0017 | Retira `quiz_preguntas` y `progreso` | Destructiva (aprobada en HU-B-312) |

## Procedimiento (protecciones de HU-B-302 / HU-B-316)
1. Respaldo de datos: `uv run python -m scripts.respaldar_datos`.
2. Revisión del SQL sin aplicarlo:
   `APP_ENV=production uv run alembic upgrade 0011:head --sql` (425 líneas; solo los 4 `DROP`
   esperados: dos columnas `duracion` y las tablas `quiz_preguntas` y `progreso`).
3. Aplicación: `APP_ENV=production uv run alembic -x confirmar=production upgrade head`
   (`-x` va **antes** del subcomando).

Con `APP_ENV=production` la configuración exige además `FLASK_DEBUG=0` y `AUTH_COOKIE_SECURE=1`;
se pasaron como variables de entorno del comando, sin editar `.env`.

## Ejecución (2026-10-23)
- Respaldo: `respaldos/20261023_224231` (14 tablas, 74 filas, revisión 0011).
- `0011 → 0012 → … → 0017` sin errores.
- Verificado: `alembic_version = 0017`; `/ruta`, `/progreso/resumen` y `/progreso/actividad`
  responden sin error.

## Criterios de aceptación
```gherkin
Escenario: Base al día
  Entonces alembic_version es 0017 y existen evaluaciones, preguntas_evaluacion e intentos_evaluacion

Escenario: Sin 500 por tablas faltantes
  Cuando consulto GET /ruta, /progreso/resumen y /progreso/actividad
  Entonces ninguno responde 500

Escenario: Respaldo previo
  Entonces existe un respaldo de los datos tomado antes de aplicar la migración
```

## Hallazgo
Hace falta un paso de despliegue que avise cuando la base está detrás del código (p. ej. comparar
`alembic_version` con `alembic heads` al arrancar en local y registrar una advertencia). Se propone
como HU futura.
