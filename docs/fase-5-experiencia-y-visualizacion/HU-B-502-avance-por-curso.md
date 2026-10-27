# HU-B-502 · Avance y estado del estudiante en cada curso

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-307, HU-B-308 |
| Rama | `hu/HU-B-502-avance-por-curso` |
| Relacionada | HU-F-504 |
| Referencia | [00-decisiones-fase-5.md](00-decisiones-fase-5.md) §2 |

## Historia
**Como** estudiante
**quiero** ver, en cada uno de mis cursos, cuánto llevo y si lo empecé, lo tengo en curso o lo terminé
**para** saber por dónde seguir y relacionarlo con la ruta del curso.

## Contexto
- `GET /cursos` devuelve solo los datos del curso. El avance existe por estudiante en
  `GET /docente/cursos/{id}/estudiantes` (vista del docente) y la ruta del estudiante en `GET /ruta?curso_id=`.
- No hay un resumen de avance **por curso** para el propio estudiante.

## Alcance
**Incluye**
1. `GET /cursos` agrega a cada curso, calculado para quien llama:
   - `docente` (`{nombre, apellido}`), `nivel`, `descripcion`.
   - `avance`: `{pct: 0–100, lecciones: {completadas, total}, ejercicios: {completados, total}, bloques_aprobados, bloques_total}`.
   - `estado`: `sin_iniciar | en_curso | finalizado` (decisiones §2; `finalizado` exige todos los
     bloques con evaluación aprobados y todas las lecciones completadas de la ruta del curso).
   - `ultimo_avance` (iso o `null`) y `retroalimentaciones_sin_leer` (entero).
2. El cálculo usa **la ruta del curso** (la propia del docente o, si no definió una, la global),
   la misma de `GET /ruta?curso_id=` y del panel del docente (HU-B-408): una sola función.
3. Filtro `?estado=` y orden `?orden=ultimo_avance|nombre|avance` (por defecto `ultimo_avance`).
4. Una consulta agregada por estudiante (no una por curso).
5. Contrato 04 §4.2 y §5.

**No incluye**
- Cursos archivados (no aparecen, como hoy).
- Avance de otros estudiantes.

## Prompt de ejecución
```text
Ejecuta HU-B-502 en SIPE-SOUND-BACKEND. Amplía GET /cursos con docente, avance {pct, lecciones,
ejercicios, bloques_aprobados, bloques_total}, estado (sin_iniciar|en_curso|finalizado),
ultimo_avance y retroalimentaciones_sin_leer, calculados con la ruta del curso (la misma función
de la ruta y de HU-B-408). Filtro ?estado= y orden ?orden=. Una consulta agregada, sin N+1.
```

## Pasos
1. Función pura de estado y porcentaje (testeable con tablas de verdad).
2. Consulta agregada por estudiante y curso.
3. Esquema de salida, filtro y orden.
4. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Sin iniciar
  Dado que me inscribí y no registré avances
  Cuando consulto GET /cursos
  Entonces el curso trae avance.pct 0 y estado "sin_iniciar"

Escenario: En curso
  Dado que completé 3 de 10 lecciones
  Entonces estado es "en_curso" y avance.pct refleja lo completado

Escenario: Finalizado
  Dado que completé todas las lecciones y aprobé todas las evaluaciones de la ruta del curso
  Entonces estado es "finalizado" y avance.pct es 100

Escenario: Misma cuenta que el docente
  Dado el mismo estudiante visto por su docente en /docente/progreso
  Entonces avance.pct coincide con el que ve el docente
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
# Dos cursos con rutas distintas: el avance de cada uno usa SU ruta.
```

## Definición de hecho específica
- [ ] Coincide con HU-B-408 (misma función, comprobado con un caso).
- [ ] Sin N+1, medido con 10 cursos.
