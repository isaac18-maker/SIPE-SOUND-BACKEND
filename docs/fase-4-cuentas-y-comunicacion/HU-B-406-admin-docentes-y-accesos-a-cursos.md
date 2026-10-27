# HU-B-406 · Administración: docentes, cursos asignados y accesos a cursos

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-405, HU-B-310 |
| Rama | `hu/HU-B-406-admin-docentes-y-cursos` |
| Relacionada | HU-F-405 |

## Historia
**Como** administrador
**quiero** ver qué cursos tiene a cargo cada docente, reasignarlos y retirar a un estudiante de un curso
**para** que ningún curso quede sin docente y cada estudiante solo acceda a los cursos que le corresponden.

## Contexto
- `cursos.docente_id` es **RESTRICT** (contrato 05): un docente con cursos no se puede eliminar
  hasta reasignarlos. Hoy no hay forma de reasignar.
- Solo el docente dueño puede retirar estudiantes (`DELETE /docente/cursos/{id}/estudiantes/{eid}`);
  el admin no tiene una vista global de cursos.

## Alcance
**Incluye** (prefijo `/api/v1/admin`, `@roles_required("admin")`)

| Endpoint | Detalle |
|---|---|
| `GET /docentes` | Paginado, `?q=`. Por docente: `id`, `nombre`, `email`, `estado` (B-405), `cursos_activos`, `cursos_archivados`, `estudiantes` (distintos en sus cursos activos), `ultimo_acceso`. |
| `GET /docentes/{id}/cursos` | Cursos del docente (activos y archivados) con `estudiantes`, `bloques_en_ruta`, `codigo_invitacion`, `creado_en`, `archivado_en`. 404 si el id no es docente. |
| `GET /cursos` | Todos los cursos, `?docente_id=&estado=activo\|archivado&q=`. |
| `PATCH /cursos/{id}/docente` | `{docente_id}` → reasigna. 422 si el destino no es docente activo. 422 si el destino es el mismo docente. Registra `reasignar_curso` **una vez por cuenta afectada** (origen y destino), para que cada una lo vea en su detalle. Las evaluaciones del curso conservan su `autor_id`. |
| `GET /cursos/{id}/estudiantes` | Igual que el endpoint del docente (reutiliza `SeguimientoService`), sin restricción de propiedad y con el correo **completo**. |
| `DELETE /cursos/{id}/estudiantes/{estudiante_id}` | Revoca el acceso: borra la inscripción (no el progreso). Registra `revocar_curso`. |
| `DELETE /usuarios/{id}/cursos` | Revoca **todas** las inscripciones de un estudiante (p. ej. cambió de colegio). Registra una acción por curso. |

1. `PATCH /admin/usuarios/{id}/rol` a `estudiante` sobre un docente con cursos activos → 409
   "Reasigna sus cursos activos (N) antes de quitarle el rol de docente."
2. Para evitar que un estudiante retirado vuelva a entrar con el código viejo, la respuesta de
   revocar sugiere en `message` regenerar el código ("Si compartió el código del curso, pídele al
   docente que lo regenere."): quien lo regenera es el docente, no el admin.
   Regenerarlo sigue siendo acción del docente (`POST /docente/cursos/{id}/codigo`).
3. Contrato 04 §4.4.

**No incluye**
- Bloquear a un estudiante de un curso para siempre (lista negra): si vuelve con un código vigente,
  entra. Se anota como posible HU.
- Pantallas (HU-F-405).

## Prompt de ejecución
```text
Ejecuta HU-B-406 en SIPE-SOUND-BACKEND. Agrega a /admin la vista de docentes con sus cursos, el
listado global de cursos, la reasignación de un curso a otro docente activo y la revocación de
inscripciones (una o todas). Reutiliza SeguimientoService para los estudiantes del curso. Cada
acción queda en acciones_admin (B-405). Quitar el rol docente con cursos activos responde 409.
No borres progreso al revocar. Sin migraciones nuevas.
```

## Pasos
1. Consultas en `SqlAdminUsuariosRepository` (docentes) y `SqlCursoRepository` (global).
2. `AdminCursosService` (reasignar, revocar) con auditoría.
3. Regla 409 en el cambio de rol.
4. Rutas y contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Cursos de un docente
  Cuando pido GET /admin/docentes/{id}/cursos
  Entonces veo sus cursos activos y archivados con el número de estudiantes

Escenario: Reasignar
  Dado un curso del docente A
  Cuando lo reasigno al docente B
  Entonces B lo ve en GET /docente/cursos y A ya no
  Y acciones_admin registra origen y destino

Escenario: Revocar acceso a un curso
  Cuando retiro a un estudiante de un curso
  Entonces el curso desaparece de su GET /cursos
  Y su progreso en lecciones y ejercicios se conserva

Escenario: Quitar rol con cursos
  Cuando cambio a "estudiante" el rol de un docente con 1 curso activo
  Entonces recibo 409 "Reasigna sus cursos activos (1) antes de quitarle el rol de docente."
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
curl -s localhost:5000/api/v1/admin/docentes -H "Authorization: Bearer $TOKEN_ADMIN"
curl -s -X PATCH localhost:5000/api/v1/admin/cursos/3/docente -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" -d '{"docente_id":"<uuid>"}'
```

## Definición de hecho específica
- [ ] Con un curso reasignado, el docente original recibe 404 en `GET /docente/cursos/{id}`.
- [ ] La revocación no borra filas de `progreso_lecciones`, `progreso_ejercicios` ni `intentos_evaluacion`.
