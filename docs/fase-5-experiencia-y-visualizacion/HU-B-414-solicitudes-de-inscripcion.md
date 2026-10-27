# HU-B-414 · Solicitudes de inscripción y ruta solo con curso

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-413 |
| Rama | `hu/HU-B-414-solicitudes-de-inscripcion` |
| Relacionada | HU-F-513, HU-F-514 |

## Historia
**Como** estudiante, docente y administrador
**quiero** que el estudiante pida entrar a un curso y que lo acepte el docente o un admin
**para** que solo vea la ruta quien tiene un curso aceptado.

## Decisiones (2026-10-26)
- El código de invitación **sigue entrando directo** (es una invitación del docente).
- Un curso sin docente solo lo resuelve un administrador.
- Los estudiantes ya inscritos se conservan.

## Alcance
**Incluye**
1. Migración 0030: `solicitudes_inscripcion` (pendiente, aceptada, rechazada) con una sola pendiente
   por curso y estudiante; las resueltas quedan como historial.
2. `GET /cursos/catalogo`, `POST` y `DELETE /cursos/{id}/solicitudes` (estudiante).
3. `GET` y `PATCH /docente/solicitudes-inscripcion`: pendientes, aceptadas y rechazadas, con
   totales por estado; aceptar crea la inscripción. Docente: sus cursos; admin: todos.
4. `GET /ruta` exige sesión y, a un estudiante, una inscripción aceptada en un curso activo.

**No incluye**
- Avisos por mensaje o correo al estudiante (se ve en su catálogo).
- Cerrar el resto de endpoints de contenido (`/lecciones`, `/ejercicios`…): siguen públicos; la
  interfaz no los muestra sin curso.

## Criterios de aceptación (Gherkin)
```gherkin
Escenario: Pedir entrar
  Cuando un estudiante pide entrar a un curso
  Entonces queda "pendiente" y el docente la ve en su panel

Escenario: Aceptar
  Cuando el docente la acepta
  Entonces el estudiante queda inscrito y ve la ruta

Escenario: Sin curso no hay ruta
  Cuando un estudiante sin inscripción pide GET /ruta
  Entonces recibe 403

Escenario: Curso sin docente
  Cuando un docente intenta resolver una solicitud de un curso sin docente
  Entonces recibe 404; solo el admin puede
```

## Definición de hecho específica
- [ ] Migración 0030 aplicada (`uv run alembic upgrade head`).
- [ ] Ninguna respuesta de solicitudes incluye correos.
