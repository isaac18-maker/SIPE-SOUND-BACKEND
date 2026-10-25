# HU-B-501 · Progreso del estudiante en cada ejercicio

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Should |
| Estimación | 3 puntos |
| Depende de | HU-B-305 |
| Rama | `hu/HU-B-501-progreso-por-ejercicio` |
| Relacionada | HU-F-503 |
| Referencia | [00-decisiones-fase-5.md](00-decisiones-fase-5.md) §2 |

## Historia
**Como** estudiante
**quiero** que la lista de ejercicios me diga cuáles ya hice, cuáles empecé y cuáles no
**para** filtrarlos por avance y saber cuál practicar hoy.

## Contexto
- `GET /ejercicios` es público y devuelve solo el catálogo. El avance del estudiante vive en
  `progreso_ejercicios` (`PUT /progreso/ejercicios/{id}`, `mejor_bpm`, `completado`) y hoy solo
  se consulta de a uno desde el detalle de la lección.

## Alcance
**Incluye**
1. `GET /ejercicios` (con sesión) agrega a cada ejercicio `mi_progreso`:
   `{estado: "sin_iniciar"|"en_curso"|"finalizado", mejor_bpm: int|null, ultimo_registro: iso|null}`.
   Sin sesión el campo no viene (`null`), así la ruta pública no cambia de forma.
2. Regla (decisiones §2): `finalizado` si `completado`; `en_curso` si hay registro (por ejemplo un
   `mejor_bpm` guardado) sin completar; `sin_iniciar` si no hay fila.
3. Filtro `?estado=` (valores del punto 1) y `?leccion_id=`; sin sesión el filtro de estado se ignora.
4. Una sola consulta (`LEFT JOIN`), sin N+1. Índice si el plan lo pide.
5. Contrato 04 §4.1 y §5.

**No incluye**
- Historial de intentos por ejercicio ni rachas.

## Prompt de ejecución
```text
Ejecuta HU-B-501 en SIPE-SOUND-BACKEND. En GET /ejercicios agrega mi_progreso por ejercicio
(estado sin_iniciar|en_curso|finalizado, mejor_bpm, ultimo_registro) con un LEFT JOIN a
progreso_ejercicios del usuario del JWT; sin sesión no se agrega. Filtros ?estado= y ?leccion_id=.
Sin N+1. Actualiza el contrato 04.
```

## Pasos
1. Repositorio: consulta con `LEFT JOIN` y filtro.
2. Servicio: regla del estado en una función pura.
3. Esquema de salida (campo opcional) y filtros.
4. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Estados
  Dado que completé el ejercicio 1, guardé un BPM en el 2 y no toqué el 3
  Cuando consulto GET /ejercicios con sesión
  Entonces el 1 es "finalizado", el 2 "en_curso" y el 3 "sin_iniciar"

Escenario: Filtro
  Cuando consulto GET /ejercicios?estado=en_curso
  Entonces solo veo los que tengo en curso

Escenario: Sin sesión
  Cuando consulto GET /ejercicios sin Authorization
  Entonces la respuesta es la de siempre y no trae mi_progreso
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
# Con datos de prueba: tres ejercicios en los tres estados; comparar con EXPLAIN que no hay N+1.
```

## Definición de hecho específica
- [ ] Un solo `SELECT` para la lista, medido.
- [ ] Contrato 04 y frontend (HU-F-503) coinciden en nombres y valores.
