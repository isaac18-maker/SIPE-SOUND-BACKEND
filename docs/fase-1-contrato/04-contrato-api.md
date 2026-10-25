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

### 4.1.1 Cuentas y sesión (HU-B-321, HU-B-322)

El backend es el **único** que habla con Supabase Auth (con la clave pública `SUPABASE_ANON_KEY`;
nunca la *service_role*). El frontend no usa `@supabase/supabase-js`.

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/auth/registro` | 🌐 (20/h por IP) | `{nombre, apellido?, email, password, acepta_terminos: true}` (el `apellido` es opcional mientras el formulario del frontend no lo envíe; pasa a obligatorio con HU-F-403) → 201 `{email, requiere_confirmacion: true}` y envía por correo un código de 6 dígitos (HU-B-402). Misma respuesta exista o no el correo. |
| POST | `/auth/verificacion` | 🌐 (10/min por IP) | `{email, codigo}` → 200 `{email, verificado: true}`. El código (6 dígitos, se aceptan espacios) vence a los 15 min, sirve una vez y se invalida tras 5 intentos fallidos. Código errado, vencido, usado o correo sin cuenta → **el mismo** 422 `REGLA_NEGOCIO` "El código no es válido o ya venció. Pide uno nuevo." |
| POST | `/auth/verificacion/reenviar` | 🌐 (5/h por IP; 1/min por cuenta) | `{email}` → siempre 200 "Si el correo tiene una cuenta pendiente, te enviamos un código nuevo." El código anterior deja de servir. |
| POST | `/auth/contrasena/olvido` | 🌐 (5/h por IP; 1 cada 2 min por cuenta) | `{email}` → siempre 200 "Si el correo tiene una cuenta, te enviamos un enlace para crear una contraseña nueva. Vence en 15 minutos." Solo envía a cuentas con el correo verificado. El enlace es `{URL_FRONTEND}/restablecer#token=…` (el token va en el **fragmento**, no en la consulta); un enlace nuevo invalida el anterior. |
| POST | `/auth/contrasena/restablecer` | 🌐 (10/min por IP) | `{token, password}` → 200 "Listo. Ya puedes iniciar sesión con tu contraseña nueva." Fija la contraseña, cierra **todas** las sesiones (renovar → 401; los `access_token` ya emitidos viven hasta vencer) y avisa por correo. Token vencido (15 min), usado o inexistente → 422 `REGLA_NEGOCIO` "El enlace ya se usó o venció. Pide uno nuevo." |
| POST | `/auth/sesion` | 🌐 (30/min por IP) | `{email, password}` → 200 `{access_token, token_type, expira_en, usuario: {id, email, nombre}}` + cookie `sipe_refresh`. 401 credenciales; 422 correo sin verificar (`meta.requiere_verificacion: true`, sin sesión ni cookie); 403 cuenta suspendida. |
| POST | `/auth/sesion/renovar` | 🍪 (60/min por IP) | Cuerpo `{}` (JSON obligatorio). Usa la cookie, la **rota** y devuelve un nuevo `access_token` con la misma forma. 401 sin cookie o vencida. |
| DELETE | `/auth/sesion` | 🍪 | Cuerpo `{}` (JSON obligatorio) y `Authorization: Bearer` opcional. Revoca el refresh token en Supabase y borra la cookie. Siempre 200. |

- **Access token**: en el cuerpo; el frontend lo guarda **en memoria** y lo envía como
  `Authorization: Bearer` (las rutas 🎓🧑‍🏫🛡️ no cambian).
- **Refresh token**: nunca en el cuerpo; solo en la cookie `sipe_refresh` (`HttpOnly`,
  `Path=/api/v1/auth`, `SameSite` según `AUTH_COOKIE_SAMESITE`, `Secure` fuera de local).
- **Peticiones con cookie**: el frontend usa `credentials: "include"`; CORS responde
  `Access-Control-Allow-Credentials: true` solo para `CORS_ORIGINS`.
- **CSRF**: `renovar` y `DELETE /auth/sesion` exigen `Content-Type: application/json`
  (un formulario de otro sitio no puede enviarlo sin *preflight*, que CORS rechaza).
- El rol **no** viaja en la sesión: se consulta con `GET /me`.
- **Cuenta sin verificar** (HU-B-402): no inicia sesión ni renueva, y cualquier ruta 🎓🧑‍🏫🛡️ responde 403
  "Confirma tu correo para continuar." aunque el `access_token` lo haya emitido Supabase directamente.
  Supabase ya no envía correos de confirmación (*Confirm email* desactivado): los envía el backend.
- **Cuenta suspendida** (HU-B-405): igual, pero 403 "Tu cuenta está suspendida. Habla con el
  administrador." en `POST /auth/sesion` y en cualquier ruta 🎓🧑‍🏫🛡️; no recibe enlaces para
  restablecer la contraseña. Los `access_token` ya emitidos viven hasta vencer; sus sesiones se cierran.

| Rol | Cómo entra |
|---|---|
| Estudiante | `POST /auth/registro`. El trigger `handle_new_user` crea el perfil con rol `estudiante` y normaliza el nombre. |
| Docente | Un admin **preautoriza** su correo; la persona se registra como cualquiera y, al **verificar** su correo con el código (`profiles.correo_verificado_en`), la base le asigna `docente`. Si ya tenía cuenta verificada, el cambio es inmediato. |

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/admin/docentes/preautorizaciones` | 🛡️ | `{email}` → 201 con `{email, estado: "pendiente" \| "aplicada", creado_en, usado_en, …}`. 409 si ya está preautorizado. |
| GET | `/admin/docentes/preautorizaciones` | 🛡️ | Lista con su estado. |
| DELETE | `/admin/docentes/preautorizaciones/{email}` | 🛡️ | Retira una **pendiente**. 409 si ya se usó (cambiar el rol con `PATCH /admin/usuarios/{id}/rol`). |

Los administradores **nunca** se crean por la API: el primero con `scripts.promover_admin`, los siguientes con `PATCH /admin/usuarios/{id}/rol` por otro admin.

### 4.2 Nuevos — estudiante (Fase 3)

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/me` | 🎓🧑‍🏫🛡️ | Perfil y rol del usuario actual: `id`, `nombre`, `apellido`, `rol`, `nivel`, `puede_editar_nombre`, `email` (el vigente en la base, no el del token) y `correo_verificado_en`. |
| PATCH | `/me` | 🎓🧑‍🏫🛡️ (10/min) | `{nombre?, apellido?}` (al menos uno) → 200 con el perfil. 403 "El administrador no ha habilitado el cambio de nombre en tu cuenta." si `puede_editar_nombre` es `false` (los admins siempre pueden). Cualquier otro campo (`rol`, `nivel`…) → 400. |
| POST | `/me/reautenticacion` | 🎓🧑‍🏫🛡️ (5/h por persona) | Paso 1 para cambiar correo o contraseña. `{password_actual}` → 200 `{enviado_a: "a***@colegio.edu.co"}` y envía un código de 6 dígitos (10 min, un solo uso) al correo **actual**. 401 "La contraseña actual no coincide." |
| POST | `/me/reautenticacion/confirmar` | 🎓🧑‍🏫🛡️ (10/min) | Paso 2. `{codigo}` → 200 `{token_reautenticacion, expira_en}`. El token vive 5 min, sirve **una vez**, está atado a la persona y a la **sesión** del JWT (reclamo `session_id`) y autoriza **un** cambio. Código errado, vencido o usado → 422 "El código no es válido o ya venció. Pide uno nuevo." |
| PATCH | `/me/contrasena` | 🎓🧑‍🏫🛡️ (10/min) | `{token_reautenticacion, password_nueva}` → 200. Cierra las **demás** sesiones (esta sigue abierta) y avisa por correo. 422 "La contraseña nueva debe ser distinta de la actual." (el token no se gasta). Token inválido, usado, vencido o de otra sesión → 422 "Vuelve a confirmar tu identidad." |
| POST | `/me/correo` | 🎓🧑‍🏫🛡️ (10/min) | `{token_reautenticacion, email_nuevo}` → 200 y envía un código (15 min) al correo **nuevo**; el correo no cambia todavía. 409 "Ese correo ya está en uso." (el token no se gasta); 422 si es el mismo correo. |
| POST | `/me/correo/confirmar` | 🎓🧑‍🏫🛡️ (10/min) | `{codigo}` → 200 `{email}`. Cambia el correo, avisa al correo **anterior** y cierra las demás sesiones. |

> Ninguna de estas rutas necesita permiso del administrador. Cambiar el nombre es otra cosa (HU-B-407).
| GET | `/ruta?curso_id=` | 🌐🎓 | Bloques con estado (`bloqueado`, `disponible`, `aprobado`), mejor puntaje y `acordes` (distintos, en orden de lección, máx. 6; HU-B-324). Sin sesión: todos `disponible`, sin puntajes. |
| GET | `/evaluaciones/{id}` | 🎓 | Evaluación sin respuestas correctas. |
| POST | `/evaluaciones/{id}/intentos` | 🎓 | Presentar intento → calificación. |
| GET | `/evaluaciones/{id}/intentos` | 🎓 | Historial propio de intentos. |
| PUT | `/progreso/lecciones/{leccion_id}` | 🎓 | Upsert progreso de lección. |
| PUT | `/progreso/ejercicios/{ejercicio_id}` | 🎓 | Upsert progreso de ejercicio. |
| GET | `/progreso/resumen` | 🎓 | Totales y último avance. |
| GET | `/progreso/actividad?dias=` | 🎓 | `dias` 7–90 (28 por defecto). `recientes` (10 eventos de lección, ejercicio o evaluación, del más reciente), `por_dia` (`fecha`, `registros`; días vacíos incluidos, zona America/Bogota) y `dias_con_practica`. Cuenta registros de avance, no minutos (HU-B-324). |
| POST | `/cursos/unirse` | 🎓 | Body `{ codigo }`. |
| GET | `/cursos` | 🎓 | Cursos **activos** donde está inscrito, con su avance (HU-B-502): `id`, `nombre`, `descripcion`, `nivel`, `docente` (`{nombre, apellido}`; también `docente_nombre` y `docente_apellido`), `inscrito_en`, `retroalimentaciones_sin_leer`, `avance` (`pct` 0–100 = lecciones completadas de **la ruta del curso** / lecciones de esa ruta, igual que el panel del docente; `lecciones` y `ejercicios` `{completadas\|completados, total}`; `bloques_aprobados` y `bloques_total`), `estado` (`sin_iniciar` sin ningún registro en esa ruta; `finalizado` con todas las lecciones completadas y las evaluaciones globales publicadas de sus bloques aprobadas; `en_curso` lo demás) y `ultimo_avance` (en esa ruta, o `null`). `?estado=sin_iniciar\|en_curso\|finalizado` filtra y `?orden=ultimo_avance\|nombre\|avance` ordena (por defecto, el avance más reciente primero; los que no empezaron al final). Una sola consulta agregada. |
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
| GET · POST | `/docente/lecciones` | Lecciones propias (admin: todas) con `?estado=&bloque_id=&q=&pagina=&por_pagina=` / crear en `borrador`. |
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
| GET | `/docente/progreso` | Panel de progreso (HU-B-408). `?curso_id=` opcional (sin él: todos tus cursos **activos**); el admin puede pasar `?docente_id=` (un docente lo ignora). `data.cursos[]`: `id`, `nombre`, `estudiantes`, `avance_promedio`, `estudiantes_al_dia` (último avance ≤ 7 días), `sin_actividad_14_dias` y `bloques[]` de **su** ruta (la del curso o, si no definió la suya, la global) con `aprobados`, `intentos`, `promedio_mejor_puntaje` y `pregunta_mas_fallada` (`{enunciado (≤ 120), fallos}` o `null`). `data.necesitan_apoyo[]` (máx. 20, primero quienes reprobaron): `estudiante_id`, `nombre`, `apellido`, `curso_id`, `curso`, `ultimo_avance`, `motivos` (`"reprobo_bloque"`: 2 o más intentos reprobados en un bloque sin aprobar; `"sin_actividad"`: nada en 14 días) y `bloque_reprobado` (`{bloque_id, titulo, intentos_reprobados}` o `null`). Curso ajeno, archivado o inexistente → 404. |
| GET | `/docente/progreso/matriz` | Estudiantes × bloques de la ruta de **un** curso (`?curso_id=` obligatorio). `?q=&orden=nombre\|-avance_pct\|-ultimo_avance&pagina=&por_pagina=` (≤ 100). Por estudiante: `estudiante_id`, `nombre`, `apellido`, `avance_pct`, `ultimo_avance` y `bloques: [{bloque_id, estado: bloqueado\|disponible\|aprobado, mejor_puntaje, intentos}]` en el orden de la ruta. El encabezado va en `meta.bloques` (`{bloque_id, numero, titulo, orden}`). El estado usa la misma regla de desbloqueo que la ruta del estudiante. |
| GET | `/docente/progreso/estudiantes/{estudiante_id}` | Progreso de un estudiante en **todos** tus cursos activos donde está inscrito: `{estudiante_id, nombre, apellido, cursos: [{curso_id, inscrito_en, bloques, intentos_del_curso, retroalimentaciones}]}`. 404 si no es estudiante tuyo. |

Ninguna respuesta de `/docente/progreso*` incluye correos (ni siquiera enmascarados).

### 4.4 Administración (Fase 3)

| Método | Ruta | Descripción |
|---|---|---|
| PATCH | `/admin/usuarios/{id}/rol` | Asignar `docente`/`estudiante`. 409 "Reasigna sus cursos activos (N) antes de quitarle el rol de docente." si un docente con cursos activos pasa a estudiante (los archivados no cuentan). |
| GET | `/admin/docentes` | Paginado, `?q=` (nombre, apellido o correo, máx. 80). Por docente: `id`, `nombre`, `apellido`, `email` (completo), `estado`, `ultimo_acceso`, `cursos_activos`, `cursos_archivados` y `estudiantes` (distintos, en sus cursos activos). |
| GET | `/admin/docentes/{id}/cursos` | Cursos del docente, **activos primero** y luego archivados: `id`, `nombre`, `descripcion`, `nivel`, `codigo_invitacion`, `creado_en`, `archivado_en`, `estudiantes`, `bloques_en_ruta`. 404 si la cuenta no es de un docente. |
| GET | `/admin/cursos` | Todos los cursos, paginado. Filtros `?docente_id=&estado=activo\|archivado&q=` (nombre del curso, del docente o código). Cada fila trae `docente` y `docente_apellido`. |
| PATCH | `/admin/cursos/{id}/docente` | `{docente_id}` → pasa el curso (también si está archivado) a otro docente **con la cuenta activa**: 422 si el destino es un estudiante, un docente sin verificar o suspendido, o el mismo docente. Los estudiantes y las evaluaciones se mantienen (cada evaluación conserva su `autor_id`). Registra `reasignar_curso` en la cuenta de origen y en la de destino. |
| GET | `/admin/cursos/{id}/estudiantes` | Igual que `/docente/cursos/{id}/estudiantes` (`?q=&orden=&pagina=&por_pagina=`), sin restricción de propiedad y con el correo **completo**. |
| DELETE | `/admin/cursos/{id}/estudiantes/{estudiante_id}` | Revoca el acceso: borra la inscripción, **no** el progreso del estudiante. 404 si no estaba inscrito. El mensaje recuerda que, si compartió el código, el docente debe regenerarlo. Registra `revocar_curso`. |
| DELETE | `/admin/usuarios/{id}/cursos` | Revoca **todas** sus inscripciones en cursos activos → `{revocadas: N}`. Registra una acción `revocar_curso` por curso. |
| PATCH | `/admin/usuarios/{id}/permisos` | `{puede_editar_nombre: bool}` → permite o impide que esa persona cambie su nombre y apellido. 404 si no existe. |
| POST | `/admin/usuarios/permisos` | `{usuario_ids: [uuid] (1–100), puede_editar_nombre: bool}` → `{actualizados: N}`; los ids que no existen se ignoran y salen en `meta.no_encontrados`. |
| GET | `/admin/usuarios` | Paginado. Filtros `?rol=&estado=pendiente_verificacion\|activa\|suspendida&q=` (nombre, apellido o correo, máx. 80), `?puede_editar_nombre=` y orden `?orden=nombre\|-creado_en\|-ultimo_acceso`. Cada fila: `id`, `nombre`, `apellido`, `email` (**completo**: el admin lo necesita), `rol`, `estado`, `puede_editar_nombre`, `creado_en`, `ultimo_acceso`, `correo_verificado_en`, `suspendido_en`, `motivo_suspension`, `ultimo_envio_verificacion` (`{estado: "enviado"\|"fallido", creado_en}` o `null`) y `cursos` (inscripciones activas; para docentes, cursos a cargo activos). `meta.totales` = cuentas por estado, sin depender de los filtros. |
| GET | `/admin/usuarios/{id}` | La fila anterior + `inscripciones`, `cursos_a_cargo` (activos y archivados), `progreso` (solo estudiantes, igual a `/progreso/resumen`) y `acciones` (últimas 20 del administrador sobre la cuenta). |
| POST | `/admin/usuarios/{id}/verificacion/reenviar` | Código nuevo al correo de una cuenta **sin verificar**; el anterior deja de servir. 409 si ya está verificada; 429 si hubo un código hace menos de 1 minuto. El resultado del envío se ve en `ultimo_envio_verificacion`. |
| POST | `/admin/usuarios/{id}/verificacion` | Verificación **manual** `{motivo}` (10–300): marca el correo como verificado sin el código (aplica el rol docente si está preautorizado). 409 si ya está verificada. |
| PATCH | `/admin/usuarios/{id}/estado` | `{estado: "suspendida", motivo}` (motivo 10–300, obligatorio) o `{estado: "activa"}` → `{id, estado}`. Suspender cierra todas sus sesiones. 403 sobre otro admin o sobre uno mismo. |
| DELETE | `/admin/usuarios/{id}` | Cuerpo `{confirmacion: "<correo de la cuenta>"}`. Borra la cuenta, su perfil, progreso, intentos e inscripciones; **no se deshace**. 422 si la confirmación no coincide; 409 "Reasigna sus cursos a cargo (N) antes de eliminar la cuenta." (docentes, cuenta cursos activos y archivados); 403 sobre admins o sobre uno mismo. |

Toda acción del administrador sobre una cuenta (reenviar, verificar a mano, suspender, reactivar, eliminar, cambiar rol, permiso de nombre, reasignar y revocar cursos) queda en `acciones_admin` con su motivo; nunca con contraseñas, códigos ni el correo completo de una cuenta eliminada.
| GET · POST | `/admin/bloques` | Catálogo global de la ruta (todos los estados). |
| GET · PATCH · DELETE | `/admin/bloques/{id}` | `DELETE` → 409 si tiene lecciones o evaluaciones (archivar). |
| PATCH | `/admin/bloques/{id}/estado` | Igual que lecciones. |

### 4.5 Mensajería interna (Fase 4, HU-B-409)

Para cualquier persona con sesión (🎓🧑‍🏫🛡️). **No envía correos** y **nunca devuelve correos**: el
remitente va como `{nombre, apellido, rol}` (o `null` si su cuenta ya no existe).

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/mensajes` | Nuevo: `{alcance, destinatario_id?, curso_id?, asunto, cuerpo}`. Respuesta: `{respuesta_a_id, cuerpo}` (el destino, el hilo y el asunto son los del mensaje original; mandar otro campo es 400). → 201 `{id, hilo_id, destinatarios: N}`. 403 si el destino no está permitido; 422 si nadie lo recibiría (cuentas sin verificar o suspendidas no reciben); 429 al pasar el límite. |
| GET | `/mensajes` | Bandeja de **hilos**. `?filtro=recibidos\|enviados\|no_leidos\|archivados` (por defecto `recibidos`), `?q=` (asunto), `?pagina=&por_pagina=`. Cada hilo: `hilo_id`, `asunto`, `alcance`, `curso`, `no_leidos`, `archivado` y `ultimo` (`remitente`, `propio`, `extracto` ≤ 140, `creado_en`). |
| GET | `/mensajes/hilos/{hilo_id}` | `{hilo_id, asunto, puede_responder, responder_a, mensajes[]}`; cada mensaje: `id`, `propio`, `remitente`, `cuerpo`, `alcance`, `curso`, `creado_en`, `nuevo` (no lo había leído antes de abrir el hilo). Los marca como leídos. `responder_a` es el `id` a enviar como `respuesta_a_id`. 404 si no participas. |
| PATCH | `/mensajes/hilos/{hilo_id}` | `{archivado?: bool, leido?: bool}` (al menos uno). `leido: false` deja sin leer solo el último mensaje **recibido**. Una respuesta nueva desarchiva el hilo. |
| GET | `/mensajes/no-leidos` | `{total}`: mensajes recibidos sin leer en hilos no archivados (el frontend lo consulta cada 60 s). |
| GET | `/mensajes/destinatarios` | `?q=` (2–80, opcional). Hasta 20 `{tipo: usuario\|curso\|grupo, id, etiqueta, detalle}`. Estudiante: solo los docentes de sus cursos activos (con el nombre del curso). Docente: sus grupos (`estudiantes_docente`, `rol_docente`, `rol_admin`) y cursos activos; con `q`, también sus estudiantes y los demás docentes y admins. Admin: `rol_estudiante`, `rol_docente`, `rol_admin`, `todos`; con `q`, personas por nombre (nunca por correo). Sin `q` no se lista a las personas. |

**Quién puede escribirle a quién** (una sola implementación, `MensajeriaService`):

| Remitente | `alcance` permitidos |
|---|---|
| admin | `usuario` (cualquiera), `rol_estudiante`, `rol_docente`, `rol_admin`, `todos` |
| docente | `usuario` (un estudiante de un curso **activo** suyo, o cualquier docente o admin), `curso` (suyo y activo), `estudiantes_docente`, `rol_docente`, `rol_admin` |
| estudiante | `usuario`, solo a un docente de un curso activo donde está inscrito |

- `destinatario_id` solo con `alcance: usuario`; `curso_id` solo con `alcance: curso`.
- Los destinatarios de un grupo se copian **en el momento del envío**: quien entra después al curso no ve avisos viejos.
- Un estudiante puede responder a su docente, pero no a un aviso del administrador. Solo se responden mensajes **recibidos**.
- Límites por hora (los mide la base): estudiante 20, docente 60, admin 120 mensajes; y 10 avisos de grupo (`alcance` ≠ `usuario`) por remitente.

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
  "estudiante_id": "uuid", "nombre": "Ana", "apellido": "Gómez", "email": "a***@colegio.edu.co",
  "avance_pct": 46, "bloques_aprobados": 2, "ultimo_avance": "…",
  "inscrito_en": "…"
}
```

> El correo del estudiante se entrega **enmascarado** al docente (protección de
> datos de menores, Ley 1581 de 2012).

## 6. Compatibilidad

No hay modo de compatibilidad (retirado en HU-B-319):
- `/api/*` sin versión, `GET /progreso`, `POST /progreso` y `/quiz/*` responden 404.
  Los quizzes son evaluaciones: `GET /ruta` da el `evaluacion_id` de cada bloque y se usan
  `GET /evaluaciones/{id}` y `POST /evaluaciones/{id}/intentos` (HU-B-308, HU-B-312).
  El progreso se registra con `PUT /progreso/lecciones/{id}` y
  `PUT /progreso/ejercicios/{id}`, y se consulta con `GET /progreso/resumen`.
- `duracion` (texto) ya no existe en lecciones ni ejercicios: usar `duracion_min` (entero).

## 7. Límites de los campos (HU-B-320)

Cada límite se aplica **tres veces**: en el formulario del frontend, en la API
(`app/core/longitudes.py` → esquemas Pydantic, error `400 VALIDACION`) y en la
base (CHECK, revisión `0013`). Cambiar uno exige cambiar los tres en PRs enlazados.
Los textos se recortan (`trim`) antes de medir; "   " no es un valor válido.
Desde HU-B-322 el registro y el inicio de sesión pasan por la API (`app/schemas/auth.py`),
así que nombre, correo y contraseña se validan en el formulario, en la API y en Supabase/la base.

### 7.1 Vigentes

| Campo | Tipo | Regla | Base |
|---|---|---|---|
| `nombre` (persona, `POST /auth/registro`) | texto | 2–80; solo letras (con tildes y ñ), espacios, `'`, `.` y `-`; espacios repetidos se colapsan (formulario y API) | `handle_new_user` lo normaliza a 2–80 y `profiles` lo exige con CHECK |
| `apellido` (persona, registro y `PATCH /me`) | texto | igual que `nombre`: 2–80, solo letras, espacios, `'`, `.` y `-`; espacios repetidos se colapsan; opcional | CHECK `apellido` 2–80 o nulo y sin caracteres de control (revisión `0023`) |
| `email` (registro e inicio de sesión) | correo | máx. 254; formato `usuario@dominio.tld`; se pasa a minúsculas (formulario y API) | Supabase Auth |
| `email` (preautorizar docente) | correo | máx. 254; formato; se guarda en minúsculas (API) | CHECK en `docentes_preautorizados` |
| `password` (registro) | contraseña | 8–72; al menos una letra y un número; **no** se recorta (formulario y API) | Supabase Auth (configurar mínimo 8, letras y dígitos) |
| `password` (inicio de sesión) | contraseña | 1–72, sin mínimo por cuentas antiguas (formulario y API) | Supabase Auth |
| `password_actual` (reautenticación) | contraseña | 1–72, sin recortar | Supabase Auth |
| `password_nueva` (cambiar contraseña) | contraseña | igual que el registro: 8–72, al menos una letra y un número; distinta de la actual | `fijar_contrasena` repite la regla (revisión `0021`) |
| `email_nuevo` (cambiar correo) | correo | igual que el registro: máx. 254, formato `usuario@dominio.tld`, minúsculas | `cambiar_correo` valida formato, largo y unicidad (revisión `0022`) |
| `token_reautenticacion` | texto | exactamente 43 caracteres `A–Z a–z 0–9 _ -` | HMAC `^[0-9a-f]{64}$`; vigencia 5 min (el CHECK permite hasta 15) |
| `token` (restablecer contraseña) | texto | exactamente 43 caracteres `A–Z a–z 0–9 _ -` (`secrets.token_urlsafe(32)`) | HMAC `^[0-9a-f]{64}$`; vigencia ≤ 15 min (CHECK) |
| `password` (restablecer contraseña) | contraseña | igual que el registro: 8–72, al menos una letra y un número, sin recortar | `fijar_contrasena` repite la regla (revisión `0021`) |
| `codigo` (verificar correo) | código | exactamente 6 dígitos; se quitan los espacios ("482 913") | `^[0-9a-f]{64}$` del HMAC; vigencia ≤ 15 min (CHECK) |
| `acepta_terminos` | booleano | debe ser `true` (formulario y API, HU-B-323) → "Debes aceptar los términos y condiciones." | — |
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
| `mensajes.asunto` | texto | 3–120 (sin contar espacios de los extremos) | 3–120 |
| `mensajes.cuerpo` | texto largo | 1–4000 | 1–4000 |
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
