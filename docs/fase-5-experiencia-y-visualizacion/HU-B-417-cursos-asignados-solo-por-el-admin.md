# HU-B-417 · Los cursos del docente los asigna solo el administrador

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-401, HU-B-406, HU-B-412, HU-B-413 |
| Rama | `hu/HU-B-417-cursos-asignados-solo-por-el-admin` |
| Relacionada | HU-F-518 |

## Historia
**Como** administrador
**quiero** ser el único que asigna y quita docentes de los cursos, y que el docente reciba un correo cuando le asigno uno
**para** controlar quién enseña cada curso y que el docente se entere sin tener que entrar a revisar.

## Decisiones (2026-10-27)
- **Reemplaza** el autoservicio de HU-B-413: el docente ya no se asigna, no se retira y no crea cursos.
  Siguen existiendo los cursos sin docente (los crea el admin) y `cursos.docente_id` NULL.
- Un docente **sin cursos activos asignados** puede entrar, pero no crea contenido: lecciones,
  ejercicios y evaluaciones se crean **dentro de la ruta de un curso suyo**.
- El correo de asignación no revierte la asignación si falla: queda en `envios_correo` como `fallido`
  (igual que el resto de correos, HU-B-401).

## Contexto
- `app/api/v1/docente.py` expone hoy `POST /docente/cursos` (crear), `GET /docente/cursos/disponibles`,
  `POST /docente/cursos/{id}/asignarme` y `POST /docente/cursos/{id}/retirarme`
  (`CursoService.crear`, `disponibles`, `asignarse`, `retirarse` en `app/services/curso_service.py`).
- `app/api/v1/admin_cursos.py` ya tiene `POST /admin/cursos` (con o sin docente) y
  `PATCH /admin/cursos/{id}/docente` (reasignar, exige un docente de origen y uno de destino).
- Los correos viven en `app/services/correo_service.py` y `app/templates/correo/` (tipos en
  `app/core/constants.py`).

## Alcance
**Incluye**
1. **Se retiran** `POST /docente/cursos`, `GET /docente/cursos/disponibles`,
   `POST /docente/cursos/{id}/asignarme` y `POST /docente/cursos/{id}/retirarme`
   (404: la ruta deja de existir). Se borran también los métodos del servicio y sus consultas que
   solo ellos usaban. Un docente sigue editando, archivando y regenerando el código de **sus** cursos.
2. **Asignar y quitar, solo admin** (`/api/v1/admin`, `@roles_required("admin")`):
   - `PATCH /cursos/{id}/docente` `{docente_id}`: ahora también sirve para un curso **sin docente**
     (asignar) además de reasignar. 422 si el destino no es docente activo o ya es el docente del curso.
   - `DELETE /cursos/{id}/docente`: el curso queda **disponible**; sus estudiantes, ruta y
     evaluaciones se conservan. 409 si ya no tenía docente.
   - `POST /cursos` con `docente_id` también dispara el correo.
3. **Correo `curso_asignado`** (tipo nuevo en `app/core/constants.py`, plantilla `.html` y `.txt`
   con la paleta del proyecto y el logo, como las otras seis): saluda por el nombre, nombra el
   curso, su nivel y cuántos estudiantes tiene, y trae el botón "Abrir mi curso" al curso en el
   panel del docente (`{url_base}/docente/cursos/{id}`). Se envía **después** de confirmar la
   transacción, al docente de destino, en asignar, reasignar y crear con docente.
   Al docente de origen (reasignación o quitar) **no** se le envía nada en esta HU.
4. **Contenido solo con curso asignado**: crear lección, ejercicio o evaluación (`/docente/...`)
   exige al menos un curso activo asignado (403 "Necesitas un curso asignado por el administrador
   para crear contenido."). Crear queda limitado a bloques que recorren sus cursos activos
   (alcance de HU-B-412). Editar, publicar y archivar lo que ya tenía no cambia.
5. **Auditoría** (`acciones_admin`): `asignar_curso` y `quitar_docente_curso`, además de
   `reasignar_curso` que ya existe. Si `acciones_admin.accion` tiene restricción `CHECK`, la
   migración 0032 la amplía (si no la tiene, esta HU no lleva migración).
6. Contrato 04 §4.3 y §4.4: se eliminan los endpoints retirados y se agregan los nuevos.

**No incluye**
- Aviso por correo al docente que pierde un curso (posible HU).
- Solicitudes del docente al admin para pedir un curso.
- Pantallas (HU-F-518).

## Prompt de ejecución
```text
Ejecuta HU-B-417 en SIPE-SOUND-BACKEND. Retira de /docente la creación de cursos, "disponibles",
"asignarme" y "retirarme" (rutas, servicio y consultas que solo ellos usaban). En /admin permite
asignar un docente a un curso sin docente con PATCH /cursos/{id}/docente, quitarlo con
DELETE /cursos/{id}/docente (el curso queda disponible y los estudiantes siguen inscritos) y
registra asignar_curso / quitar_docente_curso en acciones_admin. Agrega el correo curso_asignado
(tipo en constants.py + plantilla html y txt con la paleta y el logo de las existentes) y envíalo
al docente de destino DESPUÉS de confirmar la transacción, sin revertir la asignación si el envío
falla. Un docente sin cursos activos recibe 403 al crear lección, ejercicio o evaluación. No toques
la forma de las respuestas existentes. Actualiza el contrato 04. Sin pruebas unitarias.
```

## Pasos
1. Quitar rutas y métodos de autoservicio; revisar que ningún otro módulo los importe.
2. `AdminCursosService`: asignar, quitar docente, auditoría y envío del correo tras confirmar.
3. Plantilla `curso_asignado` y su registro en `CORREOS`; revisar el render con `StrictUndefined`.
4. Guardia de "curso asignado" al crear contenido (`ContenidoService` / servicios de lección,
   ejercicio y evaluación).
5. Contrato 04 y, si hace falta, revisión 0032.

## Criterios de aceptación
```gherkin
Escenario: El docente ya no se asigna
  Cuando un docente llama POST /docente/cursos/3/asignarme
  Entonces recibo 404

Escenario: El docente ya no crea cursos
  Cuando un docente llama POST /docente/cursos
  Entonces recibo 404

Escenario: Asignar un curso disponible
  Dado un curso sin docente
  Cuando el admin hace PATCH /admin/cursos/3/docente con un docente activo
  Entonces el curso aparece en GET /docente/cursos de ese docente
  Y se le envía el correo "curso_asignado" con el nombre del curso
  Y acciones_admin registra asignar_curso

Escenario: Quitar al docente
  Cuando el admin hace DELETE /admin/cursos/3/docente
  Entonces el curso queda sin docente y disponible para el admin
  Y los estudiantes siguen inscritos

Escenario: Falla el correo
  Dado que el servidor SMTP no responde
  Cuando el admin asigna el curso
  Entonces la asignación queda guardada y envios_correo registra el envío como fallido

Escenario: Docente sin curso crea contenido
  Dado un docente sin cursos activos
  Cuando crea una lección
  Entonces recibo 403 "Necesitas un curso asignado por el administrador para crear contenido."

Escenario: Docente con curso crea contenido
  Dado un docente con un curso activo cuya ruta incluye el bloque 2
  Cuando crea una lección en el bloque 2
  Entonces se crea; en un bloque fuera de sus cursos recibe 404
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
curl -s -X POST localhost:8000/api/v1/docente/cursos/3/asignarme -H "Authorization: Bearer $TOKEN_DOCENTE"   # 404
curl -s -X PATCH localhost:8000/api/v1/admin/cursos/3/docente -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" -d '{"docente_id":"<uuid>"}'
# Revisar la bandeja del docente y la tabla envios_correo (tipo curso_asignado)
```

## Definición de hecho específica
- [ ] El correo `curso_asignado` se ve bien en claro y oscuro, con el logo y el botón (captura en el PR).
- [ ] Ninguna consulta pierde cursos sin docente (HU-B-413).
- [ ] No quedó código muerto de las cuatro rutas retiradas.
- [ ] Si hubo revisión 0032: `check_migrations.py` en verde y `upgrade → downgrade → upgrade` probado.
