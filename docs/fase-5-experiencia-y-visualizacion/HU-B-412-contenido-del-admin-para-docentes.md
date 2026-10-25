# HU-B-412 · El docente gestiona el contenido del administrador en sus cursos

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-309, HU-B-311, HU-B-411 (la migración 0028 sigue a la 0027) |
| Rama | `hu/HU-B-412-contenido-del-admin-para-docentes` |
| Relacionada | HU-F-511 |

## Historia
**Como** docente con un curso asignado
**quiero** ver, editar y publicar el contenido y las evaluaciones que creó el administrador para mi curso
**para** adaptarlos a mi grupo sin pedirle al administrador cada cambio, sabiendo quién los creó y quién los tocó.

## Alcance
**Incluye**
1. **Alcance del docente**: además de lo suyo, lecciones, ejercicios y evaluaciones **globales** de
   los bloques que recorren sus cursos activos (la ruta propia del curso o, si no definió la
   suya, la global). Las evaluaciones propias del curso ya las gestionaba.
2. **Puede**: ver, editar, publicar, archivar (lecciones y ejercicios) y cerrar o publicar
   evaluaciones. **No puede borrar** lo que no creó (403: "Solo quien creó… Puedes archivarlo / cerrarla").
3. **Autoría**: migración 0028 con `actualizado_por` en lecciones, ejercicios y evaluaciones. Las
   respuestas traen `autor` y `modificado_por` (nombre, nunca el correo); `modificado_por` es
   `null` si nadie lo ha modificado desde que se creó.
4. **Privacidad**: los resultados de una evaluación global, vistos por un docente, solo incluyen
   a **sus** estudiantes (la evaluación reúne a todos los cursos).
5. Contrato 04 §4.3.

**No incluye**
- Que el docente cree evaluaciones globales ni borre contenido ajeno.
- Historial de ediciones (solo la última).

## Criterios de aceptación (Gherkin)
```gherkin
Escenario: Editar contenido del admin
  Dado una lección del admin en un bloque de la ruta de mi curso
  Cuando la edito
  Entonces se guarda y "modificado_por" es mi nombre

Escenario: Publicar una evaluación del admin
  Cuando cambio a publicada una evaluación global de un bloque de mi ruta
  Entonces el estado cambia y queda registrado quién lo hizo

Escenario: Borrar lo ajeno
  Cuando intento borrar una lección del admin
  Entonces recibo 403 y se me sugiere archivarla

Escenario: Fuera de mis cursos
  Cuando abro una lección de un bloque que ninguno de mis cursos recorre
  Entonces recibo 404

Escenario: Estudiantes de otros
  Cuando veo los resultados de una evaluación global
  Entonces solo aparecen mis estudiantes
```

## Definición de hecho específica
- [ ] Migración 0028 aplicada (`uv run alembic upgrade head`) y guardia de migraciones en verde.
- [ ] Un docente no ve ni nombres ni correos de estudiantes ajenos.
