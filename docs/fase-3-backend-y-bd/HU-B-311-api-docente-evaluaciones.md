# HU-B-311 · API del panel docente: gestionar evaluaciones y ver resultados

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-308, HU-B-310 |
| Rama | `hu/HU-B-311-docente-evaluaciones` |

## Implementación (2026-10-24)
- `GestionEvaluacionService` reutiliza `CursoService.curso_propio` (propiedad del curso).
- Resultados en 4 consultas agregadas fijas. El "mejor intento" de cada estudiante es el de
  mayor puntaje (empate: el más reciente); `aciertos_pct` sale de sus `respuestas` (jsonb).
- La clave `porcentaje_aprobacion` del ejemplo se llama **`aprobaron_pct`** (% de estudiantes que
  aprobaron) para no confundirla con el umbral, que sale como `minimo_requerido`.
  También se entrega `sin_presentar` (inscritos sin intentos).
- Con intentos: no se reemplazan preguntas ni se cambia `porcentaje_aprobacion` (422);
  `DELETE` → 409 con `errors: ["sugerencia: cerrar"]`. `cerrada` es final.
- `fecha_limite` debe ser futura y con zona horaria (ISO-8601).

## Historia
**Como** docente
**quiero** crear evaluaciones para mi curso, publicarlas con fecha límite y analizar los resultados
**para** medir el aprendizaje de mi grupo y reforzar los temas más débiles.

## Alcance
**Incluye** (prefijo `/api/v1/docente`):
- `GET/POST /evaluaciones?curso_id=` · `GET/PATCH/DELETE /evaluaciones/{id}`.
- `PUT /evaluaciones/{id}/preguntas`: reemplaza el conjunto completo. **422** si ya hay intentos.
- `PATCH /evaluaciones/{id}/estado`: `borrador → publicada → cerrada`. No se publica sin al menos 1 pregunta.
- `GET /evaluaciones/{id}/resultados`:
  ```json
  {
    "data": {
      "intentos": 57, "estudiantes_que_presentaron": 22, "estudiantes_del_curso": 25,
      "promedio_mejor_puntaje": 74, "porcentaje_aprobacion": 68,
      "preguntas": [ { "id": 12, "enunciado": "…", "aciertos_pct": 41 } ],
      "estudiantes": [ { "estudiante_id": "…", "nombre": "…", "mejor_puntaje": 80, "intentos": 3, "aprobado": true } ]
    }
  }
  ```
- `DELETE`: con intentos → 409 (`sugerencia: "cerrar"`); sin intentos → borrado físico (cascada a preguntas).
- Validaciones: 1–50 preguntas; 2–6 opciones; `respuesta_correcta` dentro del rango; `porcentaje_aprobacion` 50–100; `fecha_limite` futura.
- Las evaluaciones de **bloque** (globales) solo las edita un admin.

## Prompt de ejecución
```text
Ejecuta HU-B-311 en SIPE-SOUND-BACKEND.
- Reutiliza CursoService para validar propiedad del curso.
- Resultados en consultas agregadas (sin N+1). aciertos_pct por pregunta se
  calcula a partir de intentos_evaluacion.respuestas (jsonb) del mejor intento
  de cada estudiante.
- Transiciones de estado en un diccionario único, igual que en HU-B-309.
```

## Criterios de aceptación
```gherkin
Escenario: Preguntas bloqueadas tras el primer intento
  Dado una evaluación publicada con 1 intento
  Cuando el docente reemplaza sus preguntas
  Entonces recibe 422 REGLA_NEGOCIO

Escenario: Fecha límite
  Dado una evaluación con fecha_limite pasada
  Cuando un estudiante envía un intento
  Entonces recibe 422

Escenario: Pregunta más difícil
  Dado resultados donde la pregunta 12 tiene 41 % de aciertos y es la menor
  Cuando consulto /resultados
  Entonces la pregunta 12 aparece primera al ordenar por aciertos_pct ascendente
```

## Verificación manual
```bash
curl -s -H "Authorization: Bearer $TOKEN_DOCENTE" localhost:5000/api/v1/docente/evaluaciones/7/resultados | python -m json.tool
```

## Definición de hecho específica
- [ ] Ningún endpoint de estudiante expone `respuesta_correcta` antes de enviar el intento (revisión con grep de schemas `*Out`).
