# HU-B-408 · Panel de progreso del docente sobre sus cursos

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-310, HU-B-308, HU-B-407 |
| Rama | `hu/HU-B-408-panel-de-progreso` |
| Relacionada | HU-F-406 |

## Historia
**Como** docente
**quiero** ver en un solo lugar cómo avanzan los estudiantes de todos mis cursos, bloque por bloque
**para** decidir a quién apoyar y qué tema repasar en la próxima clase sin abrir estudiante por estudiante.

## Contexto
- B-310 ya da, por curso, la lista de estudiantes con `avance_pct`, `bloques_aprobados` y
  `ultimo_avance`, y el detalle de un estudiante. El docente ya puede retirar estudiantes y
  enviar retroalimentación.
- Falta la vista transversal: estudiantes × bloques, cifras por curso y quién necesita apoyo.

## Alcance
**Incluye** (prefijo `/api/v1/docente`, `@roles_required("docente","admin")`; el docente solo ve
sus cursos activos; el admin puede pasar `?docente_id=`)

| Endpoint | Detalle |
|---|---|
| `GET /progreso` | `?curso_id=` opcional (sin él: todos los cursos activos del docente). Devuelve `cursos` (por curso: `estudiantes`, `avance_promedio`, `estudiantes_al_dia` (último avance ≤ 7 días), `sin_actividad_14_dias` y **sus** `bloques`, porque cada curso puede tener su propia ruta: `aprobados`, `intentos`, `promedio_mejor_puntaje` y `pregunta_mas_fallada` con `enunciado` recortado a 120), y `necesitan_apoyo` (máx. 20): estudiantes sin actividad en 14 días **o** con 2+ intentos reprobados en un bloque que no han aprobado. Cada uno trae `motivos` (lista de códigos `"sin_actividad"`, `"reprobo_bloque"`; el frontend arma el texto) y `bloque_reprobado`. |
| `GET /progreso/matriz` | `?curso_id=` **obligatorio**, paginado por estudiante (`por_pagina` ≤ 100), `?orden=nombre\|-avance_pct\|-ultimo_avance`, `?q=`. Por estudiante: `estudiante_id`, `nombre`, `apellido`, `avance_pct`, `ultimo_avance` y `bloques: [{bloque_id, estado: bloqueado\|disponible\|aprobado, mejor_puntaje, intentos}]` en el orden de la ruta. |
| `GET /progreso/estudiantes/{estudiante_id}` | Progreso de un estudiante en **todos** los cursos del docente donde está inscrito (reutiliza el detalle de B-310 por curso). 404 si no es estudiante suyo. |

1. Consultas en `SqlProgresoDocenteRepository` (agregan por **todos** los cursos y estudiantes del
   alcance a la vez: 3 sentencias para el resumen y 5 para una página de la matriz, sin
   importar cuántos cursos o estudiantes haya) con la definición de ruta de B-310; el estado
   del bloque se calcula con la misma regla que `RutaService` (desbloqueo por intento aprobado).
2. Correo del estudiante **no** se incluye (el panel no lo necesita; B-310 lo da enmascarado).
3. Contrato 04 §4.3.

**No incluye**
- Exportar (el frontend genera CSV de la vista, como en HU-F-309).
- Gráficos (los arma el frontend con estos datos).
- Notificaciones automáticas a estudiantes sin actividad (posible HU sobre B-409).

## Prompt de ejecución
```text
Ejecuta HU-B-408 en SIPE-SOUND-BACKEND. Agrega GET /docente/progreso, /docente/progreso/matriz y
/docente/progreso/estudiantes/{id}. El docente solo ve estudiantes inscritos en sus cursos
activos; el admin puede filtrar por docente_id. Reutiliza la CTE de la ruta y la regla de
desbloqueo existentes (no dupliques lógica de RutaService). La matriz es una sola sentencia por
página. No expongas correos. Sin migraciones salvo un índice si la medición lo justifica (dilo en el PR).
```

## Pasos
1. Consultas y medición (EXPLAIN ANALYZE con 40 estudiantes × 8 bloques).
2. `ProgresoDocenteService` y esquemas de salida.
3. Rutas y contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Matriz de un curso
  Dado un curso con 25 estudiantes y una ruta de 6 bloques
  Cuando pido GET /docente/progreso/matriz?curso_id=3
  Entonces veo 25 filas con 6 estados cada una, en el orden de la ruta

Escenario: Necesitan apoyo
  Dado un estudiante sin avances en 15 días
  Cuando pido GET /docente/progreso
  Entonces aparece en necesitan_apoyo con motivo "sin_actividad"

Escenario: Curso ajeno
  Cuando pido la matriz de un curso de otro docente
  Entonces recibo 404

Escenario: Estudiante en dos cursos
  Dado un estudiante inscrito en dos de mis cursos
  Cuando pido GET /docente/progreso/estudiantes/{id}
  Entonces veo su progreso en ambos
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
curl -s "localhost:5000/api/v1/docente/progreso/matriz?curso_id=3" -H "Authorization: Bearer $TOKEN_DOCENTE"
```

## Definición de hecho específica
- [ ] Medición de la matriz (sentencias por request y tiempo) en el PR.
- [ ] Ningún campo `email` en las respuestas de `/docente/progreso*`.
