# 04 · Contrato de API (fuente de verdad compartida con el frontend)

> El frontend (`SIPE-SOUND-FULLSTACK/docs/fase-1-contrato/04-consumo-api.md`)
> referencia este archivo. **Cualquier cambio aquí exige actualizar ambos repos
> en PRs enlazados.**

## 1. Convenciones generales

| Aspecto | Regla |
|---|---|
| Prefijo | **Solo** `/api/v1`. El prefijo `/api/*` sin versión se retiró en HU-B-319 (responde 404). |
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
| 409 | `CONFLICTO` | Duplicados, o borrar contenido con progreso registrado (el `message` sugiere archivar). |
| 422 | `REGLA_NEGOCIO` | Ej. presentar evaluación de un bloque bloqueado. |
| 429 | `DEMASIADAS_SOLICITUDES` | Límite de intentos superado (p. ej. unirse a un curso). |
| 500 | `ERROR_INTERNO` | Cualquier otro. El mensaje **nunca** expone detalles internos. |
| 503 | `SERVICIO_NO_DISPONIBLE` | El servidor no puede atender la petición por ahora. |

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

### 4.1.1 Cuentas (HU-B-321)

El backend **no crea cuentas** ni guarda claves de Supabase:

| Rol | Cómo entra |
|---|---|
| Estudiante | El frontend llama a `supabase.auth.signUp` (con `options.data.nombre`). El trigger `handle_new_user` crea el perfil con rol `estudiante` y normaliza el nombre. |
| Docente | Un admin **preautoriza** su correo; la persona se registra como cualquiera y, al **confirmar** su correo, la base le asigna `docente`. Si ya tenía cuenta confirmada, el cambio es inmediato. |

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/admin/docentes/preautorizaciones` | 🛡️ | `{email}` → 201 con `{email, estado: "pendiente" \| "aplicada", creado_en, usado_en, …}`. 409 si ya está preautorizado. |
| GET | `/admin/docentes/preautorizaciones` | 🛡️ | Lista con su estado. |
| DELETE | `/admin/docentes/preautorizaciones/{email}` | 🛡️ | Retira una **pendiente**. 409 si ya se usó (cambiar el rol con `PATCH /admin/usuarios/{id}/rol`). |

Los administradores **nunca** se crean por la API: el primero con `scripts.promover_admin`, los siguientes con `PATCH /admin/usuarios/{id}/rol` por otro admin.

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

No hay modo de compatibilidad (retirado en HU-B-319):
- `/api/*` sin versión, `GET /progreso` y `POST /progreso` responden 404.
  El progreso se registra con `PUT /progreso/lecciones/{id}` y
  `PUT /progreso/ejercicios/{id}`, y se consulta con `GET /progreso/resumen`.
- `duracion` (texto) ya no existe en lecciones ni ejercicios: usar `duracion_min` (entero).

## 7. Límites de los campos (HU-B-320)

Cada límite se aplica **tres veces**: en el formulario del frontend, en la API
(`app/core/longitudes.py` → esquemas Pydantic, error `400 VALIDACION`) y en la
base (CHECK, revisión `0013`). Cambiar uno exige cambiar los tres en PRs enlazados.
Los textos se recortan (`trim`) antes de medir; "   " no es un valor válido.
Excepción: el registro va directo del frontend a Supabase Auth (HU-B-321), así que nombre,
correo y contraseña los protegen el formulario, la configuración de Supabase y la base.

### 7.1 Vigentes

| Campo | Tipo | Regla | Base |
|---|---|---|---|
| `nombre` (persona, registro con Supabase Auth) | texto | 2–80; solo letras (con tildes y ñ), espacios, `'`, `.` y `-` (formulario) | `handle_new_user` lo normaliza a 2–80 y `profiles` lo exige con CHECK |
| `email` (registro e inicio de sesión) | correo | máx. 254; formato `usuario@dominio.tld` (formulario) | Supabase Auth |
| `email` (preautorizar docente) | correo | máx. 254; formato; se guarda en minúsculas (API) | CHECK en `docentes_preautorizados` |
| `password` | contraseña | 8–72; al menos una letra y un número; **no** se recorta (formulario) | Supabase Auth (configurar mínimo 8, letras y dígitos) |
| `acepta_terminos` | booleano | debe estar marcado (formulario) | — |
| `codigo` (unirse a curso) | código | exactamente 8; `A–Z` y `2–9` sin `0 O 1 I L`; se acepta en minúsculas y con espacios a los lados | `^[A-HJKMNP-Z2-9]{8}$` |
| `cursos.nombre` | texto | 3–120 | 3–120 |
| `cursos.descripcion` | texto largo | máx. 2000 (opcional) | máx. 2000 |
| `bloques.titulo`, `lecciones.titulo`, `ejercicios.nombre` | texto | 3–120 | 3–120 |
| `bloques/lecciones/ejercicios.descripcion` | texto largo | máx. 2000 (opcional) | máx. 2000 |
| `lecciones.contenido` | texto largo | máx. 20000 | máx. 20000 |
| `lecciones.acordes`, `ejercicios.acordes` | lista | máx. 24 elementos de 1–20 caracteres | igual |
| `lecciones.temas` | lista | máx. 20 elementos de 1–60 caracteres | igual |
| `ejercicios.pasos` | lista | máx. 30 elementos de 1–300 caracteres | igual |
| `duracion_min` | entero | 1–600 (opcional) | 1–600 |
| `ejercicios.bpm_recomendado`, `mejor_bpm` | entero | 20–300 | 20–300 |
| `ejercicios.compas` | texto | `N/D` con N ∈ {2,3,4,5,6,7,9,12} y D ∈ {2,4,8} (p. ej. `4/4`, `6/8`) | mismo patrón |
| `acordes.nombre` | texto | 1–20 | 1–20 |
| `acordes.descripcion` | texto | máx. 500 | máx. 500 |
| `porcentaje` | entero | 0–100 | 0–100 |
| `retroalimentaciones.mensaje` | texto largo | 1–1000 | 1–1000 |
| `nivel` | opción | `principiante`, `intermedio`, `avanzado` | mismo conjunto |

### 7.2 Para las HU pendientes (se aplican al crearlas)

| Campo | HU | Regla |
|---|---|---|
| `evaluaciones.titulo` | HU-B-308 | 3–120 |
| `preguntas.enunciado` | HU-B-308 | 3–300 |
| `preguntas.opciones` | HU-B-308 | 2–6 opciones de 1–120 caracteres, sin repetidas |
| `evaluaciones.descripcion` | HU-B-308 | máx. 2000 |
| `evaluaciones.porcentaje_aprobacion` | HU-B-308 | entero 50–100 |
| `evaluaciones.intentos_maximos` | HU-B-308 | entero 1–10 o vacío |
| `evaluaciones.fecha_limite` | HU-B-308 | futura o vacía |
| `?q=` (búsqueda) | HU-B-310 | máx. 80 |
| `?pagina`, `?por_pagina` | todas | `pagina ≥ 1`; `por_pagina` 1–100 |
