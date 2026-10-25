# HU-B-403 · Restablecer la contraseña con un enlace de un solo uso

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-402 |
| Rama | `hu/HU-B-403-restablecer-contrasena` |
| Relacionada | HU-F-402 |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §2, §4.1 |

## Historia
**Como** estudiante o docente que olvidó su contraseña
**quiero** recibir un enlace por correo que me deje elegir una nueva
**para** volver a entrar sin pedir ayuda, sabiendo que ese enlace no le sirve a nadie más después.

## Contexto
- HU-B-322 dejó fuera la recuperación de contraseña: hoy no existe ningún flujo.
- `CodigoService` (B-402) ya emite y consume códigos; `CorreoService` (B-401) ya tiene la
  plantilla `restablecer_contrasena` y `contrasena_cambiada`.
- Sin la clave *service_role* no se puede fijar la contraseña por la API de Supabase.

## Alcance
**Incluye**
1. Revisión `0021_fijar_contrasena` (esquema), funciones `SECURITY DEFINER`, `set search_path = ''`,
   `EXECUTE` revocado a `public`, `anon`, `authenticated`:
   - `public.fijar_contrasena(p_usuario uuid, p_password text)`: `update auth.users set
     encrypted_password = extensions.crypt(p_password, extensions.gen_salt('bf', 10)), updated_at = now()`.
     Rechaza (excepción) si la contraseña no cumple 8–72 con letras y números.
   - `public.cerrar_sesiones(p_usuario uuid, p_excepto uuid default null)`: borra las filas de
     `auth.sessions` del usuario (sus `auth.refresh_tokens` caen por cascada), salvo la sesión `p_excepto`.
2. `CodigoService` con formato **token**: `secrets.token_urlsafe(32)`, mismo HMAC y mismas reglas
   (15 min, un solo uso, código nuevo invalida el anterior). El token no tiene "intentos": es inadivinable.
3. Rutas (contrato 04 §4.1.1):
   - `POST /auth/contrasena/olvido` 🌐 (5/h por IP, 1 cada 2 min por correo): `{email}` → **siempre**
     200 "Si el correo tiene una cuenta, te enviamos un enlace para crear una contraseña nueva. Vence en 15 minutos."
     Solo se envía a cuentas verificadas y no suspendidas.
   - `POST /auth/contrasena/restablecer` 🌐 (10/min por IP): `{token, password}` → 200
     "Listo. Ya puedes iniciar sesión con tu contraseña nueva." Token vencido, usado o inexistente →
     422 "El enlace ya se usó o venció. Pide uno nuevo."
4. Al restablecer, en **una** transacción: consumir el token → `fijar_contrasena` → `cerrar_sesiones`
   (todas) → enviar `contrasena_cambiada` al correo de la cuenta (fecha y hora en America/Bogota).
5. Enlace del correo: `{URL_FRONTEND}/restablecer#token=<token>` (fragmento, no consulta).
6. Esquemas `OlvidoContrasenaIn` y `RestablecerContrasenaIn` (`password` con las reglas de
   `RegistroIn`, `extra="forbid"`).
7. Contrato 04 (§4.1.1 y §7: `token` 43 caracteres base64url).

**No incluye**
- Cambiar la contraseña con sesión iniciada (B-404).
- Bloquear la cuenta por muchos pedidos (el límite por IP y por correo basta en esta etapa).

## Prompt de ejecución
```text
Ejecuta HU-B-403 en SIPE-SOUND-BACKEND. Implementa POST /auth/contrasena/olvido y
POST /auth/contrasena/restablecer. El token es secrets.token_urlsafe(32), se guarda solo su HMAC
en codigos_verificacion (proposito restablecer_contrasena), vence en 15 minutos y se consume con
un UPDATE atómico: no puede usarse dos veces. "olvido" responde siempre lo mismo. Fija la
contraseña con la función SECURITY DEFINER public.fijar_contrasena (revisión 0021, EXECUTE
revocado a public/anon/authenticated) y cierra todas las sesiones del usuario. Sin service_role.
Nunca registres el token ni la contraseña.
```

## Pasos
1. Revisión 0021 con `downgrade()` (borra las funciones).
2. Formato token en `CodigoService`.
3. Servicio `RecuperacionService` y rutas.
4. Aviso `contrasena_cambiada`.
5. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Restablecer
  Dado una cuenta verificada
  Cuando pido el enlace y envío POST /auth/contrasena/restablecer con el token y "nueva1234"
  Entonces recibo 200
  Y puedo iniciar sesión con "nueva1234" y no con la anterior
  Y recibo un correo "Tu contraseña cambió"

Escenario: Un solo uso
  Dado que ya usé un enlace
  Cuando lo envío otra vez con otra contraseña
  Entonces recibo 422 "El enlace ya se usó o venció. Pide uno nuevo."

Escenario: Vencido a los 15 minutos
  Dado un enlace emitido hace 16 minutos
  Cuando lo uso
  Entonces recibo 422 y la contraseña no cambia

Escenario: Sin enumeración
  Cuando pido el enlace para un correo que no existe
  Entonces recibo el mismo 200 y no se envía ningún correo

Escenario: Sesiones cerradas
  Dado que tengo sesión abierta en otro navegador
  Cuando restablezco la contraseña
  Entonces POST /auth/sesion/renovar en ese navegador responde 401

Escenario: Sin RPC
  Cuando el rol anon ejecuta public.fijar_contrasena
  Entonces PostgreSQL responde permiso denegado
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
# CORREO_MODO=archivo: pedir el enlace, copiar el token del .eml, restablecer,
# iniciar sesión con la nueva contraseña (prueba de compatibilidad con Supabase Auth).
```

## Definición de hecho específica
- [ ] Inicio de sesión real con la contraseña fijada por `fijar_contrasena` (evidencia en el PR).
- [ ] El token no aparece en logs del backend ni en el `Referer` (va en el fragmento).
- [ ] `has_function_privilege('anon', 'public.fijar_contrasena(uuid,text)', 'execute')` = `false`.
