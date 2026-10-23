# 04 · Contrato de API (fuente de verdad compartida con el frontend)

> El frontend (`SIPE-SOUND-FULLSTACK/docs/fase-1-contrato/04-consumo-api.md`)
> referencia este archivo. **Cualquier cambio aquí exige actualizar ambos repos
> en PRs enlazados.**

## 1. Convenciones generales

| Aspecto | Regla |
|---|---|
| Prefijo | `/api/v1`. Se mantiene `/api/*` (sin versión) solo durante la transición de la Fase 2 y se elimina en HU-B-312. |
| Formato | JSON UTF-8. Fechas ISO-8601 en UTC (`2026-10-21T14:05:00Z`). |
| Nombres de campos | `snake_case`, en español, iguales a las columnas cuando aplique. |
| Recursos | Sustantivos en plural. Acciones no-CRUD como sub-recurso verbal: `POST /evaluaciones/{id}/intentos`. |
| Autenticación | `Authorization: Bearer <access_token de Supabase>`. |
| Autorización | Por rol (`estudiante`, `docente`, `admin`) **y** por propiedad del recurso. |
| Idempotencia | `PUT` y `DELETE` idempotentes. `POST` crea. `PATCH` actualiza parcialmente. |
| CORS | Solo orígenes de `CORS_ORIGINS`. |

## 2. Estructura única de respuesta (HU-B-317)

**Todas** las respuestas de `/api/v1`, de éxito y de error, tienen la misma forma:

```json
{
  "statusCode": 200,
  "status": "OK",
  "data": { "id": 3, "titulo": "Acordes mayores C y G" },
  "success": true,
  "message": "Operación exitosa.",
  "errors": [],
  "timestamp": "2026-10-22T06:00:13.562Z",
  "meta": {}
}
```

| Campo | Contenido |
|---|---|
| `statusCode` | Código HTTP (igual al de la respuesta). |
| `status` | Éxito: nombre HTTP (`OK`, `CREATED`). Error: código de la tabla de la sección 3. |
| `data` | El recurso o la lista; `null` en los errores. |
| `success` | `true` si `statusCode` < 400. |
| `message` | Texto en español para mostrar al usuario. |
| `errors` | Lista de textos con el detalle (p. ej. `"porcentaje: Debe ser menor o igual a 100."`); vacía si no hay. |
| `timestamp` | Momento de la respuesta, ISO-8601 UTC con milisegundos. |
| `meta` | Datos adicionales, p. ej. paginación `{ "pagina": 1, "por_pagina": 20, "total": 42 }`. |

- Paginación por query: `?pagina=1&por_pagina=20` (máx. 100).
- Filtros por query con nombre de campo: `?nivel=principiante&bloque_id=2`.
- Orden: `?orden=numero` / `?orden=-creado_en`.
- Swagger (`/docs`, solo `local` y `staging`) documenta esta estructura como `RespuestaEstandar`.

## 3. Errores

```json
{
  "statusCode": 400,
  "status": "VALIDACION",
  "data": null,
  "success": false,
  "message": "Hay campos con errores.",
  "errors": ["porcentaje: Debe ser menor o igual a 100."],
  "timestamp": "2026-10-22T06:00:13.562Z",
  "meta": {}
}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDACION` | Cuerpo o parámetros inválidos. |
| 401 | `NO_AUTENTICADO` | Falta token o es inválido/expirado. |
| 403 | `SIN_PERMISO` | Rol insuficiente o recurso ajeno. |
| 404 | `NO_ENCONTRADO` | El recurso no existe **o** el usuario no tiene derecho a saber que existe. |
| 409 | `CONFLICTO` | Duplicados, o borrar contenido con progreso registrado (`details.sugerencia = "archivar"`). |
| 422 | `REGLA_NEGOCIO` | Ej. presentar evaluación de un bloque bloqueado. |
| 429 | `DEMASIADAS_SOLICITUDES` | Límite de intentos superado (p. ej. unirse a un curso). |
| 500 | `ERROR_INTERNO` | Cualquier otro. El mensaje **nunca** expone detalles internos. |

## 4. Catálogo de endpoints

Leyenda de acceso: 🌐 público · 🎓 estudiante · 🧑‍🏫 docente · 🛡️ admin.

### 4.1 Existentes (Fase 2 los mueve a `/api/v1` sin cambiar comportamiento)

| Método | Ruta | Acceso | Respuesta |
|---|---|---|---|
| GET | `/health` | 🌐 | `{ status, mensaje }` |
| GET | `/bloques` | 🌐 | Lista ordenada por `orden_index`. |
| GET | `/lecciones` | 🌐 | Lista ordenada por `numero`. |
| GET | `/lecciones/{id}` | 🌐 | Detalle. |
| GET | `/ejercicios` | 🌐 | Lista. |
| GET | `/acordes` | 🌐 | Lista con `diagram` (`frets`, `fingers`, `baseFret`, `barre`). |
| GET | `/quiz/{bloque_id}` | 🌐 | Preguntas **sin** `respuesta_correcta`. |
| POST | `/quiz/{bloque_id}/verificar` | 🎓 | Calificación + detalle. |
| GET | `/progreso` | 🎓 | Progreso del usuario actual. |
| POST | `/progreso` | 🎓 | Upsert de progreso. |

### 4.2 Nuevos — estudiante (Fase 3)

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/me` | 🎓🧑‍🏫🛡️ | Perfil y rol del usuario actual. |
| GET | `/ruta?curso_id=` | 🌐🎓 | Bloques con estado (`bloqueado`, `disponible`, `aprobado`) y mejor puntaje. Sin sesión: todos `disponible`, sin puntajes. |
| GET | `/evaluaciones/{id}` | 🎓 | Evaluación sin respuestas correctas. |
| POST | `/evaluaciones/{id}/intentos` | 🎓 | Presentar intento → calificación. |
| GET | `/evaluaciones/{id}/intentos` | 🎓 | Historial propio de intentos. |
| PUT | `/progreso/lecciones/{leccion_id}` | 🎓 | Upsert progreso de lección. |
| PUT | `/progreso/ejercicios/{ejercicio_id}` | 🎓 | Upsert progreso de ejercicio. |
| GET | `/progreso/resumen` | 🎓 | Totales y último avance. |
| POST | `/cursos/unirse` | 🎓 | Body `{ codigo }`. |
| GET | `/cursos` | 🎓 | Cursos donde está inscrito. |
| GET | `/cursos/{id}/retroalimentaciones` | 🎓 | Mensajes del docente para él. |

### 4.3 Nuevos — panel docente (Fase 3, prefijo `/docente`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/docente/resumen` | Totales: cursos, estudiantes, evaluaciones pendientes, actividad reciente. |
| GET · POST | `/docente/cursos` | Listar / crear cursos propios. |
| GET · PATCH · DELETE | `/docente/cursos/{id}` | Detalle / editar / archivar (soft delete). |
| POST | `/docente/cursos/{id}/codigo` | Regenerar código de invitación. |
| PUT | `/docente/cursos/{id}/bloques` | Definir ruta del curso: `[{ bloque_id, orden }]`. |
| GET | `/docente/cursos/{id}/estudiantes` | Lista con % de avance, último acceso, bloques aprobados. |
| GET | `/docente/cursos/{id}/estudiantes/{estudiante_id}` | Detalle: progreso por lección/ejercicio e intentos. |
| DELETE | `/docente/cursos/{id}/estudiantes/{estudiante_id}` | Retirar del curso (borra inscripción). |
| POST | `/docente/cursos/{id}/estudiantes/{estudiante_id}/retroalimentaciones` | Enviar comentario. |
| GET · POST | `/docente/lecciones` | Lecciones propias / crear. |
| GET · PATCH · DELETE | `/docente/lecciones/{id}` | Detalle / editar / borrar (409 si tiene progreso → archivar). |
| PATCH | `/docente/lecciones/{id}/estado` | `borrador` · `publicado` · `archivado`. |
| GET · POST | `/docente/ejercicios` | Igual que lecciones. |
| GET · PATCH · DELETE | `/docente/ejercicios/{id}` | |
| PATCH | `/docente/ejercicios/{id}/estado` | |
| GET · POST | `/docente/evaluaciones` | Por curso (`?curso_id=`). |
| GET · PATCH · DELETE | `/docente/evaluaciones/{id}` | Incluye preguntas **con** respuesta correcta. |
| PUT | `/docente/evaluaciones/{id}/preguntas` | Reemplaza el set de preguntas (solo si no hay intentos). |
| PATCH | `/docente/evaluaciones/{id}/estado` | Publicar / cerrar. |
| GET | `/docente/evaluaciones/{id}/resultados` | Intentos por estudiante, promedio, % aprobación, pregunta más fallada. |

### 4.4 Administración (Fase 3)

| Método | Ruta | Descripción |
|---|---|---|
| PATCH | `/admin/usuarios/{id}/rol` | Asignar `docente`/`estudiante`. |
| CRUD | `/admin/bloques` | Catálogo global de la ruta. |

## 5. Esquemas de referencia

```json
// LeccionOut
{
  "id": 3, "bloque_id": 1, "numero": 3,
  "titulo": "Acordes mayores C y G", "descripcion": "…",
  "nivel": "principiante", "duracion_min": 35,
  "acordes": ["C", "G"], "temas": ["Acordes mayores"],
  "estado": "publicado", "autor_id": "uuid|null",
  "creado_en": "…", "actualizado_en": "…"
}

// IntentoOut
{
  "id": "uuid", "evaluacion_id": 7, "puntaje": 80,
  "correctas": 4, "total": 5, "aprobado": true,
  "minimo_requerido": 80,
  "detalle": { "12": { "correcta": true, "respuesta_correcta": 1 } },
  "creado_en": "…"
}

// EstudianteCursoOut (panel docente)
{
  "estudiante_id": "uuid", "nombre": "Ana", "email": "a***@colegio.edu.co",
  "avance_pct": 46, "bloques_aprobados": 2, "ultimo_avance": "…",
  "inscrito_en": "…"
}
```

> El correo del estudiante se entrega **enmascarado** al docente (protección de
> datos de menores, Ley 1581 de 2012).

## 6. Compatibilidad

- Mientras exista el frontend antiguo, los endpoints de 4.1 conservan su forma de
  respuesta **sin** envoltura `data` bajo `/api/*`. Bajo `/api/v1/*` ya usan la envoltura.
- La eliminación de `/api/*` sin versión se hace en HU-B-312, después de desplegar HU-F-304 y HU-F-306.
