# HU-B-418 · Monitoreo de la actividad del docente en la plataforma

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Should |
| Estimación | 8 puntos |
| Depende de | HU-B-406, HU-B-408, HU-B-417 |
| Rama | `hu/HU-B-418-monitoreo-de-actividad-del-docente` |
| Relacionada | HU-F-519 |

## Historia
**Como** administrador
**quiero** saber qué hace cada docente en la plataforma y cómo van sus cursos asignados
**para** detectar a tiempo a un docente inactivo y reasignar sus cursos antes de que sus estudiantes se queden sin acompañamiento.

## Contexto
- Hoy solo existe `ultimo_acceso` (`auth.users.last_sign_in_at`, en
  `app/repositories/sqlalchemy/admin_docentes_repository.py`), que no dice si el docente hizo algo útil.
- Lecciones y ejercicios no guardan fecha de modificación, así que la actividad **no se puede
  reconstruir** con las tablas actuales: hay que registrarla desde ahora.
- `acciones_admin` registra lo que hace el admin sobre una cuenta, no lo que hace el docente.

## Decisiones (2026-10-27)
- Se registra **qué tipo de cosa** hizo el docente y en qué curso, nunca el contenido ni datos de estudiantes.
- La actividad se conserva **180 días**; una limpieza diaria (o al registrar, por lotes) borra lo anterior.
- Estado de actividad del docente (lo calcula el backend, una sola vez): `activo` (algo en los
  últimos 7 días), `inactivo` (entre 8 y 30 días), `sin_actividad` (más de 30 días o nunca).

## Alcance
**Incluye**
1. **Migración 0032** (o la siguiente libre): tabla `actividad_docente` con `id`, `docente_id` (FK
   `profiles` CASCADE), `curso_id` (FK `cursos` SET NULL, nullable), `tipo`, `accion`, `creado_en`.
   Índices `(docente_id, creado_en desc)` y `(curso_id, creado_en desc)`. RLS activo y sin
   políticas (solo el backend), como `envios_correo`.
   - `tipo`: `sesion`, `leccion`, `ejercicio`, `evaluacion`, `retroalimentacion`, `mensaje`, `curso`.
   - `accion`: `inicio`, `creo`, `edito`, `publico`, `archivo`, `elimino`, `comento`, `envio`, `retiro_estudiante`, `regenero_codigo`, `definio_ruta`.
2. **Registro** desde los servicios existentes, en la misma transacción de la acción
   (`ActividadDocenteService.registrar`, una sola función): inicio de sesión de un docente (como
   máximo uno por hora), crear/editar/publicar/archivar/eliminar lecciones, ejercicios y
   evaluaciones, retroalimentaciones, mensajes enviados, y las acciones sobre su curso (ruta,
   código, retirar estudiante). Si registrar falla, **no** rompe la acción del docente.
3. **Endpoints** (`/api/v1/admin`, `@roles_required("admin")`):

   | Endpoint | Detalle |
   |---|---|
   | `GET /docentes/actividad` | Un renglón por docente activo: `docente_id`, `nombre`, `estado_actividad`, `ultima_actividad`, `acciones_30d`, `cursos_asignados`, `estudiantes`. Filtros `?estado_actividad=&q=` y `?orden=ultima_actividad\|-acciones_30d\|nombre`. Paginado. |
   | `GET /docentes/{id}/actividad/resumen?dias=` | `dias` 7–90 (28 por defecto). `por_dia: [{fecha, acciones}]` con días vacíos (zona America/Bogota), `por_tipo: [{tipo, acciones}]`, `dias_activos`, `ultima_actividad`, y por curso asignado: `{curso_id, nombre, estudiantes, avance_promedio_pct, estudiantes_sin_actividad_7d, ultima_actividad_docente}`. |
   | `GET /docentes/{id}/actividad` | Línea de tiempo paginada (más reciente primero): `{creado_en, tipo, accion, curso_id, curso_nombre}`. Filtros `?tipo=&curso_id=&desde=&hasta=`. |

   404 si el id no es docente. Sin correos de estudiantes ni apellidos en los agregados.
4. `ultimo_acceso` de `GET /admin/docentes` (HU-B-406) sigue igual; se agregan `estado_actividad`
   y `ultima_actividad` a ese listado para no obligar al frontend a cruzar dos consultas.
5. Reutiliza las definiciones de avance y estado de HU-B-408 / HU-B-502; no recalcula porcentajes distinto.
6. Contrato 04 §4.4 y contrato 05 (tabla nueva).

**No incluye**
- Monitorear al estudiante (ya está en HU-B-408).
- Alertas por correo al admin cuando un docente se vuelve inactivo.
- Registrar lecturas (ver pantallas) o el tiempo en pantalla.
- Pantallas (HU-F-519).

## Prompt de ejecución
```text
Ejecuta HU-B-418 en SIPE-SOUND-BACKEND. Crea la tabla actividad_docente (revisión Alembic con RLS
sin políticas e índices) y ActividadDocenteService.registrar, y llámalo dentro de la transacción
de las acciones del docente (inicio de sesión máximo una vez por hora, contenido, evaluaciones,
retroalimentaciones, mensajes y acciones sobre su curso). Un fallo al registrar no rompe la acción.
Agrega GET /admin/docentes/actividad, GET /admin/docentes/{id}/actividad/resumen y
GET /admin/docentes/{id}/actividad con los campos y filtros de la HU, y suma estado_actividad y
ultima_actividad a GET /admin/docentes. Reutiliza las definiciones de HU-B-408. Sin N+1, sin
correos de estudiantes, sin guardar el contenido de lo que el docente hizo. Actualiza los
contratos 04 y 05. Sin pruebas unitarias.
```

## Pasos
1. Modelo, repositorio y revisión 0032; limpieza de más de 180 días.
2. `ActividadDocenteService` y puntos de registro en los servicios del docente.
3. Consultas agregadas (una sentencia por endpoint, como `admin_docentes_repository`).
4. Rutas, esquemas pydantic y contratos.

## Criterios de aceptación
```gherkin
Escenario: Se registra lo que hace el docente
  Cuando un docente publica una evaluación de su curso
  Entonces GET /admin/docentes/{id}/actividad muestra "evaluacion · publico" con el nombre del curso

Escenario: Estado de actividad
  Dado un docente cuya última acción fue hace 12 días
  Cuando el admin pide GET /admin/docentes/actividad
  Entonces su estado_actividad es "inactivo"

Escenario: Resumen con días vacíos
  Cuando el admin pide el resumen de 28 días de un docente
  Entonces por_dia trae 28 elementos, con acciones 0 en los días sin actividad

Escenario: Cursos asignados con avance
  Cuando el admin abre el resumen de un docente con dos cursos
  Entonces ve para cada curso estudiantes, avance promedio y estudiantes sin actividad en 7 días

Escenario: Privacidad
  Cuando el admin consulta cualquiera de los tres endpoints
  Entonces no aparecen correos de estudiantes ni el contenido de lo que el docente escribió

Escenario: Un docente no ve esto
  Cuando un docente llama GET /admin/docentes/actividad
  Entonces recibo 403
```

## Verificación manual
```bash
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
curl -s "localhost:8000/api/v1/admin/docentes/actividad?orden=-acciones_30d" -H "Authorization: Bearer $TOKEN_ADMIN"
curl -s "localhost:8000/api/v1/admin/docentes/<uuid>/actividad/resumen?dias=28" -H "Authorization: Bearer $TOKEN_ADMIN"
```

## Definición de hecho específica
- [ ] Revisión aplicada con el procedimiento de producción (`APP_ENV=production ... -x confirmar=production`).
- [ ] Registrar la actividad no añade más de una sentencia por acción del docente.
- [ ] Ningún campo de las respuestas contiene correos de estudiantes.
