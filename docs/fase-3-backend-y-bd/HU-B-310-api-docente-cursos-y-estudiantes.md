# HU-B-310 · API del panel docente: cursos, estudiantes y retroalimentación

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-307, HU-B-308 |
| Rama | `hu/HU-B-310-docente-cursos` |

## Historia
**Como** docente
**quiero** ver a los estudiantes de cada curso que tengo a cargo con su avance real
**para** identificar quién necesita apoyo y darle retroalimentación.

## Alcance
**Incluye** (prefijo `/api/v1/docente`, `@roles_required("docente","admin")`):

| Endpoint | Detalle |
|---|---|
| `GET /resumen` | Cifras: `cursos_activos`, `estudiantes`, `evaluaciones_publicadas`, `intentos_ultimos_7_dias`. Listas (máx. 10 c/u): `sin_actividad_14_dias` (`estudiante_id`, `nombre`, `curso_id`, `curso`, `ultimo_avance`) y `actividad_reciente` (últimos intentos: `estudiante`, `evaluacion`, `puntaje`, `creado_en`). |
| `GET/POST /cursos`, `GET/PATCH/DELETE /cursos/{id}` | `DELETE` = archivar. |
| `POST /cursos/{id}/codigo` | Regenera código. |
| `PUT /cursos/{id}/bloques` | Ruta del curso. |
| `GET /cursos/{id}/estudiantes` | Paginado, orden `?orden=-avance_pct|nombre|-ultimo_avance`, filtro `?q=`. Campos de `EstudianteCursoOut` (contrato §5). |
| `GET /cursos/{id}/estudiantes/{eid}` | Progreso por bloque → lección/ejercicio, intentos por evaluación, retroalimentaciones enviadas. |
| `DELETE /cursos/{id}/estudiantes/{eid}` | Elimina la inscripción (no el progreso del estudiante). |
| `POST /cursos/{id}/estudiantes/{eid}/retroalimentaciones` | `{ mensaje }` 1–1000 caracteres. |

**Cálculo de `avance_pct`**: lecciones publicadas completadas de los bloques de la ruta del curso ÷ total de lecciones publicadas de esa ruta × 100, redondeado. Se calcula en **una** consulta agregada (no N+1).

**Privacidad**: email enmascarado (`a***@dominio`); nunca se exponen IDs de otros cursos del estudiante.

## Prompt de ejecución
```text
Ejecuta HU-B-310 en SIPE-SOUND-BACKEND.
- Todas las consultas del listado de estudiantes con una sola sentencia SQL
  (CTE o subconsultas agregadas con SQLAlchemy). Prohibido iterar estudiantes
  y consultar por cada uno.
- Toda verificación "este curso es del docente" en CursoService (un único método
  privado reutilizado), respondiendo 404 si no lo es.
- Mascara de email en una función utilitaria en app/core/privacidad.py.
- Agrega índices si EXPLAIN muestra seq scan sobre inscripciones o progreso_lecciones
  (en una revisión nueva).
```

## Criterios de aceptación
```gherkin
Escenario: Solo mis estudiantes
  Dado el docente A con el curso 1 y el docente B con el curso 2
  Cuando A consulta /docente/cursos/2/estudiantes
  Entonces recibe 404

Escenario: Avance correcto
  Dado una ruta de curso con 10 lecciones publicadas
  Y un estudiante con 4 completadas
  Cuando el docente lista estudiantes
  Entonces avance_pct es 40

Escenario: Retirar estudiante conserva su progreso
  Cuando el docente retira a un estudiante del curso
  Entonces la inscripción desaparece
  Y el progreso del estudiante en progreso_lecciones permanece

Escenario: Sin consultas N+1
  Dado un curso con 40 estudiantes
  Cuando se lista con SQLALCHEMY echo activado
  Entonces se ejecutan como máximo 3 sentencias SQL
```

## Verificación manual
```bash
SQLALCHEMY_ECHO=1 uv run python run.py
curl -s -H "Authorization: Bearer $TOKEN_DOCENTE" "localhost:5000/api/v1/docente/cursos/1/estudiantes?orden=-avance_pct"
```

## Definición de hecho específica
- [ ] El listado responde en < 300 ms con 200 estudiantes en datos semilla locales.
