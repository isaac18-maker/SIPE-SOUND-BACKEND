# HU-B-404 · Cambiar correo y contraseña con verificación de identidad

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-403 |
| Rama | `hu/HU-B-404-cambio-de-correo-y-contrasena` |
| Relacionada | HU-F-403 (Mi cuenta) |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §2, §4.1 |

## Historia
**Como** estudiante o docente con sesión iniciada
**quiero** cambiar mi correo o mi contraseña sin pedirle permiso al administrador
**para** mantener mi cuenta al día, con la seguridad de que nadie que use mi computador abierto pueda hacerlo.

## Contexto
- No existe ningún endpoint para cambiar correo o contraseña.
- B-403 creó `fijar_contrasena` y `cerrar_sesiones`; B-402, `CodigoService`.
- La sesión es un JWT de Supabase cuyo `session_id` viene en el reclamo `session_id`.

## Decisión: verificación de identidad en dos factores
Cambiar correo o contraseña exige **las dos** cosas:
1. La contraseña actual (se comprueba con Supabase `token?grant_type=password`; la sesión que
   devuelve se revoca de inmediato).
2. Un código de 6 dígitos enviado al correo **actual** (`proposito = reautenticar`, 10 min).

Si ambas son correctas, la API entrega un `token_reautenticacion` (32 bytes, guardado como HMAC,
5 minutos, un solo uso, atado al usuario y a la sesión del JWT). Con él se hace **un** cambio.

## Alcance
**Incluye**
1. `POST /me/reautenticacion` 🎓🧑‍🏫🛡️ (5/h por usuario): `{password_actual}` → si coincide,
   envía el código `reautenticacion` y responde 200 `{enviado_a: "a***@colegio.edu.co"}`.
   Contraseña incorrecta → 401 "La contraseña actual no coincide."
2. `POST /me/reautenticacion/confirmar` (10/min por usuario): `{codigo}` → 200
   `{token_reautenticacion, expira_en}`.
3. `PATCH /me/contrasena`: `{token_reautenticacion, password_nueva}` → `fijar_contrasena`,
   `cerrar_sesiones(usuario, excepto = sesión actual)` y aviso `contrasena_cambiada`. La sesión
   actual sigue abierta.
4. Cambio de correo en dos pasos:
   - `POST /me/correo`: `{token_reautenticacion, email_nuevo}` → envía `cambiar_correo` con un código
     al **nuevo** correo (`proposito = cambiar_correo`, `email_destino = nuevo`). Si el correo ya
     pertenece a otra cuenta → 409 "Ese correo ya está en uso." (la persona ya demostró su identidad).
   - `POST /me/correo/confirmar`: `{codigo}` → `public.cambiar_correo(usuario, nuevo)`, aviso
     `correo_cambiado` al correo **anterior** ("Si no fuiste tú, restablece tu contraseña…"), y
     `cerrar_sesiones(usuario, excepto = actual)`.
5. Revisión `0022_cambiar_correo` (esquema): `public.cambiar_correo(p_usuario uuid, p_email text)`
   `SECURITY DEFINER`: valida formato y unicidad (`lower(email)`), actualiza `auth.users.email`
   y `auth.identities.identity_data->>'email'` (proveedor `email`), `updated_at = now()`.
   `EXECUTE` revocado a `public`, `anon`, `authenticated`. No toca `correo_verificado_en`
   (el código ya probó el correo nuevo).
6. `GET /me` agrega `email` (de `auth.users`) y `correo_verificado_en`.
7. Esquemas con `extra="forbid"`; `password_nueva` con las reglas de registro y distinta de la actual.
8. Contrato 04 (nueva sección "Mi cuenta") y §7.

**No incluye**
- Nombre y apellido (B-407).
- Autenticación de dos factores permanente (TOTP): fuera de alcance.
- Cambiar el correo de un docente preautorizado no cambia su rol (igual que hoy).

## Prompt de ejecución
```text
Ejecuta HU-B-404 en SIPE-SOUND-BACKEND. Cambiar correo o contraseña exige contraseña actual +
código enviado al correo actual; con ambos se emite un token_reautenticacion de 5 minutos, un
solo uso, atado al usuario y al session_id del JWT. El cambio de correo además confirma un
código enviado al correo nuevo. Usa fijar_contrasena y cerrar_sesiones (B-403) y crea
public.cambiar_correo en la revisión 0022 (SECURITY DEFINER, EXECUTE revocado). Avisa por correo
al correo anterior en cada cambio. Ninguna de estas rutas necesita permiso del admin. Nunca
registres contraseñas, códigos ni tokens.
```

## Pasos
1. Revisión 0022 con `downgrade()`.
2. `ReautenticacionService` (verificar contraseña, emitir y confirmar código, emitir y consumir token).
3. `CuentaService` (cambiar contraseña, iniciar y confirmar cambio de correo).
4. Rutas en `app/api/v1/me.py`; `GET /me` ampliado.
5. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Cambiar contraseña
  Dado que inicié sesión
  Cuando confirmo mi contraseña actual y el código que llegó a mi correo
  Y envío PATCH /me/contrasena con el token y una contraseña nueva válida
  Entonces recibo 200, sigo con sesión en este navegador
  Y las demás sesiones quedan cerradas
  Y recibo el aviso "Tu contraseña cambió"

Escenario: Sin contraseña actual no hay código
  Cuando envío POST /me/reautenticacion con una contraseña equivocada
  Entonces recibo 401 y no se envía ningún correo

Escenario: Token de un solo uso
  Dado que ya usé un token_reautenticacion para cambiar la contraseña
  Cuando lo uso para cambiar el correo
  Entonces recibo 422 "Vuelve a confirmar tu identidad."

Escenario: Token de otra sesión
  Dado un token emitido en la sesión A
  Cuando lo envío desde la sesión B del mismo usuario
  Entonces recibo 422

Escenario: Cambiar correo
  Dado un token_reautenticacion vigente
  Cuando envío POST /me/correo con "nuevo@correo.co" y confirmo el código que llegó a ese correo
  Entonces puedo iniciar sesión con "nuevo@correo.co"
  Y el correo anterior recibe el aviso del cambio

Escenario: Correo ocupado
  Cuando pido cambiar a un correo de otra cuenta
  Entonces recibo 409 "Ese correo ya está en uso."
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
# Flujo completo con CORREO_MODO=archivo; inicio de sesión con el correo nuevo y con la
# contraseña nueva (compatibilidad con Supabase Auth).
```

## Definición de hecho específica
- [ ] Inicio de sesión real después de `cambiar_correo` y de `fijar_contrasena` (evidencia en el PR).
- [ ] Avisos al correo anterior en ambos cambios (captura del `.eml`).
- [ ] `has_function_privilege('authenticated', 'public.cambiar_correo(uuid,text)', 'execute')` = `false`.
