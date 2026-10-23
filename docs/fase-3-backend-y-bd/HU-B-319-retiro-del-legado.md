# HU-B-319 · Retiro inmediato del legado

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-317 |
| Rama | `hu/HU-B-319-retiro-legado` |
| Origen | Decisión del equipo (2026-10-24): retirar el legado sin esperar a HU-F-304/306 |

## Historia
**Como** equipo
**quiero** una sola versión de la API con una sola forma de respuesta
**para** no mantener dos contratos ni código de compatibilidad.

## Alcance
**Incluye**
1. Retiro del prefijo `/api/*` sin versión y del "modo legado" de respuestas y errores.
2. Retiro de `GET /progreso` y `POST /progreso` (adaptador `_a_legado`, esquema `ProgresoCreate`).
3. Revisión `0012` **destructiva aprobada**: `drop column duracion` en `lecciones` y `ejercicios`,
   con guardia (aborta si alguna fila tiene `duracion` sin `duracion_min`) y `downgrade()`
   que recrea la columna desde `duracion_min`.

**No incluye** (siguen en uso hasta HU-B-308): tablas `progreso` (resultado de bloques) y `quiz_preguntas`.

## Impacto en el frontend
El frontend actual (`src/lib/api.js`) usa `/api/*`: **deja de funcionar** hasta que
HU-F-203 lo migre a `/api/v1` con la estructura estándar. Decisión aceptada por el equipo.

## Criterios de aceptación
```gherkin
Escenario: Legado retirado
  Cuando consulto GET /api/lecciones
  Entonces recibo 404 con la estructura estándar

Escenario: Progreso legado retirado
  Cuando envío POST /api/v1/progreso
  Entonces recibo 404; el avance se registra con PUT /api/v1/progreso/lecciones/{id}

Escenario: Sin duracion en texto
  Cuando consulto GET /api/v1/lecciones/{id}
  Entonces la respuesta trae duracion_min y no trae duracion
```

## Despliegue
1. Mergear el código **antes** de aplicar `0012`: el código anterior todavía lee `duracion`.
2. Respaldo: `uv run python -m scripts.respaldar_datos`.
3. `uv run alembic upgrade head` y `uv run alembic check`.
