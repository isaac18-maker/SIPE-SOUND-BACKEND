# HU-B-413 · Cursos sin docente y asignación de docentes

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-310, HU-B-406 |
| Rama | `hu/HU-B-413-cursos-sin-docente` |
| Relacionada | HU-F-516 |

## Historia
**Como** administrador y docente
**quiero** cursos disponibles (sin docente) a los que un docente pueda asignarse o retirarse
**para** repartir los cursos sin pedir cambios manuales al administrador.

## Decisiones (2026-10-26)
- Los cursos sin docente los crea el **administrador**.
- Al retirarse un docente, el curso queda **disponible** y sus estudiantes siguen inscritos.
- El código de invitación sigue entrando directo (sin solicitud).

## Alcance
**Incluye**
1. Migración 0029: `cursos.docente_id` admite NULL (la FK sigue en RESTRICT).
2. `POST /admin/cursos` `{nombre, descripcion?, nivel, docente_id?}`: crea con o sin docente.
3. `GET /docente/cursos/disponibles`, `POST /docente/cursos/{id}/asignarme` (409 si otro se
   adelantó, atómico) y `POST /docente/cursos/{id}/retirarme`. Solo rol docente.
4. Las consultas con `join` al docente pasan a `left join` (listado del admin, mis cursos del
   estudiante, inscripciones de una cuenta).

**No incluye**
- Solicitudes de inscripción (HU-B-414) ni quién las acepta en un curso sin docente.

## Criterios de aceptación (Gherkin)
```gherkin
Escenario: Curso disponible
  Cuando el admin crea un curso sin docente
  Entonces aparece en GET /docente/cursos/disponibles

Escenario: Asignarse
  Cuando un docente pulsa asignarme
  Entonces queda a cargo y deja de estar disponible; el segundo docente recibe 409

Escenario: Retirarse
  Cuando el docente se retira
  Entonces el curso queda disponible y sus estudiantes siguen inscritos
```

## Definición de hecho específica
- [ ] Migración 0029 aplicada (`uv run alembic upgrade head`).
- [ ] Ningún listado pierde cursos sin docente.
