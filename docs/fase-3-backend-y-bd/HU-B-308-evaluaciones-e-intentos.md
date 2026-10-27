# HU-B-308 · Convertir los quizzes en evaluaciones con historial de intentos

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-307 |
| Rama | `hu/HU-B-308-evaluaciones` |

## Implementación (2026-10-24)
- Revisiones **0015** (esquema) y **0016** (datos); los números 0008/0009 ya estaban usados.
- Regla de desbloqueo única en `RutaService.estados_de_bloques`: un bloque **sin evaluación**
  no bloquea al siguiente. "Aprobado" = algún intento aprobado en la evaluación global del bloque
  (aunque luego se cierre).
- Una sola evaluación global vigente por bloque (índice único parcial `uq_evaluaciones_bloque_global`).
- `intentos_max` protegido contra envíos simultáneos con `pg_advisory_xact_lock` por estudiante.
- Los intentos copiados de `progreso` llevan `respuestas = {}` y `correctas` estimadas con el puntaje.
- `/quiz/*` delega en la evaluación del bloque y ya no escribe en `progreso`.

## Historia
**Como** estudiante
**quiero** presentar la evaluación de un bloque cuantas veces necesite y ver mi historial
**para** saber si estoy mejorando.

**Como** docente
**quiero** que cada intento quede registrado
**para** identificar qué preguntas le cuestan más a mi grupo.

## Contexto
`quiz_preguntas` está atada a `bloque_id` y el resultado se guarda en `progreso` como un único registro (mejor nota), perdiendo el historial. El umbral de 80 % está fijo en código.

## Alcance
**Incluye**
- Revisión `0008` (esquema): `evaluaciones`, `preguntas_evaluacion`, `intentos_evaluacion` con CASCADE e índices.
- Revisión `0009` (datos):
  1. Por cada `bloque_id` distinto en `quiz_preguntas` → una `evaluaciones` (`bloque_id`, `curso_id = null`, `titulo = 'Evaluación del bloque N'`, `porcentaje_aprobacion = 80`, `estado = 'publicada'`).
  2. Copiar preguntas (`pregunta` → `enunciado`, `orden_index` → `orden`).
  3. Por cada `progreso` con `tipo='bloque'` → un `intentos_evaluacion` (`puntaje = porcentaje`, `aprobado = completado`, `respuestas = '{}'`, `creado_en = actualizado_en`).
  4. Idempotente.
- `EvaluacionService` con calificación por **estrategia** (`Calificador` Protocol; implementación `CalificadorOpcionUnica`). Lee `porcentaje_aprobacion` de la evaluación.
- Reglas: `intentos_max` y `fecha_limite` se respetan (422 `REGLA_NEGOCIO`); una evaluación de bloque no se puede presentar si el bloque está bloqueado para el estudiante.
- `GET /api/v1/ruta?curso_id=` → bloques (de la ruta del curso o la global) con `estado` (`bloqueado|disponible|aprobado`), `mejor_puntaje`, `evaluacion_id` y `lecciones` publicadas con `completado`. La regla de desbloqueo vive en `RutaService` (una sola implementación para todo el sistema).
- Endpoints de estudiante: `GET /api/v1/evaluaciones/{id}`, `POST /api/v1/evaluaciones/{id}/intentos`, `GET /api/v1/evaluaciones/{id}/intentos`.
- Compatibilidad: `GET /quiz/{bloque_id}` y `POST /quiz/{bloque_id}/verificar` delegan en la evaluación del bloque.

**No incluye**: eliminar `quiz_preguntas` ni `progreso` (HU-B-312). Gestión docente (HU-B-311).

## Prompt de ejecución
```text
Ejecuta HU-B-308 en SIPE-SOUND-BACKEND.
- Separa esquema (0008) y datos (0009). 0009 no borra nada.
- La respuesta correcta NUNCA sale en endpoints de estudiante antes de enviar el intento.
- Calificación: función pura + estrategia por tipo de pregunta (principio O de SOLID).
- El intento se guarda siempre (aprobado o no). El "mejor puntaje" se calcula, no se guarda.
- Los endpoints /quiz/* existentes deben devolver exactamente lo mismo que antes.
```

## Límites de los campos
Aplica los de [04-contrato-api §7.2](../fase-1-contrato/04-contrato-api.md#72-para-las-hu-pendientes-se-aplican-al-crearlas) en el esquema Pydantic **y** con CHECK en la migración.

## Criterios de aceptación
```gherkin
Escenario: Historial
  Dado un estudiante que presenta la misma evaluación 3 veces con 40, 80 y 60
  Cuando consulta GET /evaluaciones/{id}/intentos
  Entonces ve los 3 intentos ordenados del más reciente al más antiguo
  Y el bloque sigue aprobado

Escenario: Umbral configurable
  Dado una evaluación con porcentaje_aprobacion 70
  Cuando el estudiante obtiene 70
  Entonces aprobado es true

Escenario: Bloque bloqueado
  Dado que el estudiante no aprobó el bloque 1
  Cuando intenta presentar la evaluación del bloque 2
  Entonces recibe 422 REGLA_NEGOCIO

Escenario: Estado calculado en servidor
  Dado un estudiante que aprobó el bloque 1
  Cuando consulta GET /api/v1/ruta
  Entonces el bloque 1 es "aprobado", el 2 "disponible" y el 3 "bloqueado"

Escenario: Ruta del curso
  Dado un curso cuya ruta es [bloque 3, bloque 1]
  Cuando el estudiante consulta /ruta?curso_id=<id>
  Entonces los bloques llegan en ese orden

Escenario: Compatibilidad
  Cuando el frontend actual llama POST /api/quiz/1/verificar
  Entonces recibe la misma forma de respuesta que antes
```

## Verificación manual
```bash
uv run alembic upgrade head
psql "$LOCAL" -c "select count(*) from quiz_preguntas; select count(*) from preguntas_evaluacion;"
psql "$LOCAL" -c "select count(*) from progreso where tipo='bloque'; select count(*) from intentos_evaluacion;"
```

## Definición de hecho específica
- [ ] Constante `PORCENTAJE_APROBACION` usada solo como valor por defecto al crear.
