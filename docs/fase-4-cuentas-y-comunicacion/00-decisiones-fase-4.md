# Fase 4 · Cuentas y comunicación: decisiones y modelo

> Referencia para HU-B-401 … HU-B-410 y para sus pares del frontend (HU-F-401 … HU-F-408).
> Si una HU de esta fase contradice el contrato de `docs/fase-1-contrato/`, gana el contrato
> y el agente lo reporta. Las decisiones de este documento las tomó el equipo el 2026-10-24.

## 1. Qué resuelve la fase

| Necesidad | HU backend | HU frontend |
|---|---|---|
| Enviar correos propios por Gmail SMTP con plantillas compatibles con los clientes de correo | B-401 | — |
| Código de verificación de registro (15 min, un solo uso) y reenvío | B-402 | F-401 |
| Restablecer la contraseña con un enlace de un solo uso (15 min) | B-403 | F-402 |
| Cambiar correo y contraseña con verificación de identidad, sin permiso del admin | B-404 | F-403 |
| El admin gestiona cuentas: verificación pendiente, reenvío, activas, suspender, eliminar | B-405 | F-404 |
| El admin gestiona docentes: cursos asignados, reasignar, revocar accesos a cursos | B-406 | F-405 |
| Nombre y apellido editables solo si el admin lo habilita (por usuario) | B-407 | F-403, F-404 |
| Panel de progreso del docente sobre sus cursos | B-408 | F-406 |
| Mensajería interna y avisos (admin, docente, estudiante → su docente) | B-409 | F-407 |
| Video guía de YouTube opcional en bloques, lecciones, ejercicios y acordes | B-410 | F-408 |

## 2. Decisión: el backend es dueño de los códigos y del envío de correos

**Antes** (HU-B-321/322): Supabase Auth enviaba el correo de confirmación con su SMTP y sus
plantillas; el backend solo hablaba con Supabase usando la clave pública.

**Ahora**:

| Tema | Decisión | Por qué |
|---|---|---|
| Envío | El backend envía con `smtplib` (biblioteca estándar) a `smtp.gmail.com:587` con STARTTLS y una **contraseña de aplicación** de Gmail. | Control total del remitente, las plantillas y el registro de envíos. Sin dependencias nuevas. |
| Plantillas | Jinja2 (ya viene con Flask) en `app/templates/correo/`, HTML + texto plano (`multipart/alternative`). | Se versionan y se revisan en PR; no viven en un panel externo. |
| Códigos y tokens | Tabla propia `codigos_verificacion`: solo se guarda el **HMAC-SHA256** del código, vence en ≤ 15 min (CHECK en la base) y se consume con un `UPDATE … WHERE usado_en IS NULL AND expira_en > now() RETURNING` atómico. | Un código usado, vencido o reemplazado no vuelve a servir, ni con dos peticiones simultáneas. |
| Verificación de correo | Columna propia `profiles.correo_verificado_en`. En Supabase se **desactiva** *Confirm email* (Supabase deja de enviar correos). | El backend decide quién está verificado. |
| Puerta de entrada | `POST /auth/sesion` **y** `auth_required` rechazan cuentas sin verificar o suspendidas. | La clave pública de Supabase es pública: alguien podría pedir un token directo a Supabase con una cuenta sin verificar. El backend no confía en eso. |
| Docente preautorizado | Se aplica cuando se llena `correo_verificado_en` (trigger sobre `profiles`), ya no con `auth.users.email_confirmed_at`. | Con *Confirm email* desactivado, Supabase llena `email_confirmed_at` al registrarse: el trigger viejo daría el rol docente a quien se registre con un correo ajeno. **B-402 lo reemplaza en la misma revisión.** |
| Contraseña y correo en Supabase | Funciones `SECURITY DEFINER` en `public` (con `EXECUTE` revocado a `public`, `anon` y `authenticated`), igual que `aplicar_docente_preautorizado` (revisión 0014). | Sigue sin usarse la clave *service_role* (HU-B-321). |

### 2.1 Riesgos aceptados y su mitigación

| Riesgo | Mitigación |
|---|---|
| Escribir en `auth.users` desde funciones propias depende del formato interno de Supabase (bcrypt en `encrypted_password`, `auth.identities`). | Las funciones son pequeñas, viven en una revisión con `downgrade()` y su HU incluye una verificación manual de inicio de sesión después de cada cambio. Si Supabase cambia el formato, falla la verificación, no los datos. |
| Gmail personal limita el envío (~500 destinatarios/día; Workspace ~2000). | Los correos son solo **transaccionales** (códigos, enlaces, avisos de seguridad). La mensajería interna (B-409) **no** envía correos. Límites por destinatario y por IP. |
| Un `.env` sin SMTP impide verificar cuentas. | `CORREO_MODO=archivo` (solo `APP_ENV=local`) escribe cada correo como `.eml` en `tmp/correos/`. Fuera de local, sin SMTP la app **no arranca**. |
| Ventana entre desplegar y cambiar Supabase. | Orden de despliegue de B-402 (§5). |

## 3. Estados de una cuenta

Se calculan, no se guardan como texto:

| Estado | Condición | Puede iniciar sesión |
|---|---|---|
| `pendiente_verificacion` | `correo_verificado_en IS NULL` | No (422, "Aún no confirmas tu correo…") |
| `activa` | verificado y `suspendido_en IS NULL` | Sí |
| `suspendida` | `suspendido_en IS NOT NULL` | No (403, "Tu cuenta está suspendida. Habla con el administrador.") |

## 4. Modelo de datos nuevo (revisiones tentativas, se recalculan al implementar)

| Revisión | HU | Cambio |
|---|---|---|
| 0018 | B-401 | `envios_correo`: `id uuid`, `usuario_id` (FK `profiles` **SET NULL**), `tipo`, `estado in ('enviado','fallido')`, `error` (código corto, nunca el texto del servidor SMTP con datos), `creado_en`. Índice `(usuario_id, tipo, creado_en desc)`. |
| 0019 | B-402 | `profiles.correo_verificado_en timestamptz`; `codigos_verificacion` (§4.1); trigger `on_profile_verificado`; `handle_new_user()` deja de mirar `email_confirmed_at`; se retira `on_auth_user_confirmed`. |
| 0020 | B-402 | Datos: `correo_verificado_en = auth.users.email_confirmed_at` para las cuentas ya confirmadas. |
| 0021 | B-403 | `fijar_contrasena(uuid, text)` y `cerrar_sesiones(uuid, uuid)`. |
| 0022 | B-404 | `cambiar_correo(uuid, text)`. |
| 0023 | B-405 | `profiles.suspendido_en`, `profiles.motivo_suspension`; `acciones_admin` (auditoría); `eliminar_cuenta(uuid)`. |
| 0024 | B-407 | `profiles.apellido`, `profiles.puede_editar_nombre`. |
| 0025 | B-409 | `mensajes`, `mensaje_destinatarios`. |
| 0026 | B-410 | `video_youtube_id`, `video_inicio_seg` en `bloques`, `lecciones`, `ejercicios`, `acordes`. |

### 4.1 `codigos_verificacion`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | `uuid` | PK, `gen_random_uuid()` |
| `usuario_id` | `uuid` | FK `profiles` **CASCADE**, índice |
| `proposito` | `text` | `verificar_correo` · `restablecer_contrasena` · `reautenticar` · `reautenticado` · `cambiar_correo` |
| `codigo_hash` | `text` | HMAC-SHA256 hex (64) con `CODIGOS_SECRETO`; nunca el código |
| `email_destino` | `text` | correo al que se envió (en `cambiar_correo`, el nuevo) |
| `intentos` | `int` | 0–5; al llegar a 5 el código se invalida |
| `expira_en` | `timestamptz` | CHECK `expira_en <= creado_en + interval '15 minutes'` |
| `usado_en`, `invalidado_en` | `timestamptz` | uno de los dos cierra el código |
| `creado_en` | `timestamptz` | `now()` |

- Índice único parcial: un solo código **abierto** por `(usuario_id, proposito)`
  (`WHERE usado_en IS NULL AND invalidado_en IS NULL`). Emitir uno nuevo invalida el anterior
  en la misma transacción.
- RLS activado sin políticas (solo el backend lo lee).
- Limpieza: los códigos cerrados o vencidos de más de 7 días se borran con
  `scripts/limpiar_codigos.py` (tarea programada; no es una migración).

| Propósito | Formato | Vigencia | Cómo llega |
|---|---|---|---|
| `verificar_correo` | 6 dígitos | 15 min | correo con el código |
| `restablecer_contrasena` | token de 32 bytes (`secrets.token_urlsafe`) | 15 min | enlace `URL_FRONTEND/restablecer#token=…` |
| `reautenticar` | 6 dígitos | 10 min | correo con el código |
| `cambiar_correo` | 6 dígitos | 15 min | correo al **nuevo** correo |
| `reautenticado` | token de 32 bytes, atado al `session_id` del JWT | 5 min | respuesta de la API tras `reautenticar` (B-404); autoriza un solo cambio |

> El token del enlace va en el **fragmento** (`#token=`), no en la consulta: el navegador no lo
> envía al servidor del frontend ni en el `Referer`.

## 5. Orden de despliegue (obligatorio)

```
1. B-401 en producción con SMTP configurado y un correo de prueba enviado.
2. B-402: alembic upgrade head (0019 y 0020) → desplegar la API.
3. En el mismo momento: Supabase → Authentication → Providers → Email → desactivar "Confirm email".
4. HU-F-401 en producción.
5. B-403 … B-410 en el orden de la tabla del README (cada HU de frontend después de su par).
```

Entre los pasos 2 y 3 Supabase puede enviar su propio correo además del nuestro: no rompe
nada (el código de Supabase no se usa). Lo que **no** puede pasar es el paso 3 sin el 2.

## 6. Reglas de mensajería (B-409)

| Remitente | Puede escribir a |
|---|---|
| Admin | un usuario · todos los estudiantes · todos los docentes · todos |
| Docente | un estudiante de sus cursos · todos los estudiantes de un curso suyo · todos sus estudiantes · un docente · todos los docentes · los admins |
| Estudiante | solo a los docentes de los cursos activos donde está inscrito (y responder sus mensajes) |

- La mensajería es interna: **no** envía correos (límite de Gmail y protección de menores).
- Un estudiante nunca ve el correo de nadie; un docente ve el nombre del estudiante, no su correo.

## 7. Videos guía (B-410)

- Un video **opcional** por bloque, lección, ejercicio y acorde: se guarda el id de YouTube
  (11 caracteres, `^[A-Za-z0-9_-]{11}$`) y un segundo de inicio opcional. Nunca la URL completa.
- La API acepta `watch?v=`, `youtu.be/`, `/embed/`, `/shorts/` y `m.youtube.com`, con o sin `t=`.
- Quién edita: el docente en **sus** lecciones y ejercicios; el admin en todo (los bloques y
  los acordes son catálogo global). Cambiarlo exige modificar esta tabla y B-410.
- El frontend lo reproduce desde `youtube-nocookie.com` y no carga nada de YouTube hasta que el
  estudiante pulsa reproducir (privacidad y poca conectividad).

## 8. Variables de entorno nuevas

| Variable | HU | Ejemplo / regla |
|---|---|---|
| `CORREO_MODO` | B-401 | `smtp` · `archivo` (solo local) |
| `SMTP_HOST`, `SMTP_PUERTO` | B-401 | `smtp.gmail.com`, `587` |
| `SMTP_USUARIO` | B-401 | cuenta de Gmail que envía |
| `SMTP_CLAVE_APLICACION` | B-401 | **secreta**: contraseña de aplicación de 16 caracteres (exige verificación en dos pasos en la cuenta) |
| `CORREO_REMITENTE`, `CORREO_NOMBRE_REMITENTE` | B-401 | igual a `SMTP_USUARIO` (o un alias verificado en Gmail), `SIPE-SOUND` |
| `URL_FRONTEND` | B-401 | origen del frontend para los enlaces, sin `/` final; debe estar en `CORS_ORIGINS` |
| `CODIGOS_SECRETO` | B-402 | **secreta**: 32+ bytes aleatorios para el HMAC de los códigos |

> `URL_FRONTEND` reemplaza a `FRONTEND_URL`, retirada en HU-B-321 porque ya no se usaba;
> vuelve con otro nombre y una validación nueva (debe estar en `CORS_ORIGINS`).
