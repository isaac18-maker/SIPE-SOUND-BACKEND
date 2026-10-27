# HU-B-419 · Corregir "aún no confirmaste tu correo" en una cuenta ya verificada

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-402, HU-B-405, HU-B-416 |
| Rama | `hu/HU-B-419-correo-confirmado-en-supabase` |
| Relacionada | HU-F-520 |

## Historia
**Como** persona que confirmó su correo con el código
**quiero** poder iniciar sesión
**para** no quedar atrapada en un aviso de "confirma tu correo" que no se puede resolver.

## El caso
La cuenta `reginopm0897@gmail.com` se registró y quedó pendiente. El administrador le envió el
código de confirmación (`POST /admin/usuarios/{id}/verificacion/reenviar`) y la persona lo escribió. Después:

1. El admin la ve **activa** (`profiles.correo_verificado_en` ya tiene fecha).
2. La persona **restableció su contraseña** sin problema.
3. Al **iniciar sesión** recibe "aún no has confirmado tu correo".
4. En esa pantalla, **"Pedir otro código" no envía nada**.

## Causa
Hay dos marcas de "correo confirmado" y solo una se actualiza:

| Marca | Quién la usa | ¿Se llenó? |
|---|---|---|
| `profiles.correo_verificado_en` | El backend (HU-B-402): estado del admin, restablecer contraseña, puertas de entrada | Sí, al validar el código |
| `auth.users.email_confirmed_at` | **Supabase Auth** al pedir el token (`/token?grant_type=password`) | **No**, si la cuenta nació cuando *Confirm email* estaba activo |

`SupabaseAuth.iniciar_sesion` recibe de Supabase `email_not_confirmed`, que
`app/infrastructure/supabase_auth.py` traduce a `MENSAJE_SIN_CONFIRMAR` con
`requiere_verificacion: true`. El frontend manda a la persona a `/verificar`, pero
`VerificacionService.enviar_codigo` solo envía a cuentas **sin** verificar
(`buscar_pendiente_por_email`): como esta ya lo está, responde 200 sin enviar nada. Es un
círculo sin salida.
El restablecimiento sí funcionó porque `fijar_contrasena` no pasa por esa comprobación de Supabase.

Afecta a toda cuenta creada antes de desactivar *Confirm email* en Supabase y verificada después.

## Alcance
**Incluye**
1. **Revisión 0033** (o la siguiente libre):
   - Función `public.confirmar_correo_auth(uuid)` `SECURITY DEFINER`, con `EXECUTE` solo para el
     rol del backend (igual que `fijar_contrasena`, 0021): `update auth.users set
     email_confirmed_at = coalesce(email_confirmed_at, now())`. El trigger
     `on_auth_user_confirmed` ya no existe (0019), por lo que no cambia ningún rol.
   - Dato: `email_confirmed_at = profiles.correo_verificado_en` para toda cuenta ya verificada con
     `email_confirmed_at` nulo (repara a `reginopm0897@gmail.com` y a las demás).
2. **Al verificar, se confirma en los dos lados**: `VerificacionService.verificar` y
   `AdminCuentasService.verificar_manual` llaman a `confirmar_correo_auth` en la misma
   transacción que `marcar_verificada`. También el cambio de correo confirmado (HU-B-404).
3. **Autocuración al iniciar sesión**: si Supabase responde `email_not_confirmed` **y** el perfil
   ya está verificado, el backend llama a `confirmar_correo_auth` y repite el inicio de sesión una
   sola vez. Si el perfil **no** está verificado, el aviso con `requiere_verificacion` se mantiene.
   Así el aviso solo aparece cuando de verdad falta el código.
4. **Correo con botón**: `verificar_correo.html` / `.txt` agregan el botón "Confirmar mi correo"
   que abre `{url_base}/verificar?email=<correo codificado>` (nunca el código en el enlace).
   Sirve igual para el envío del registro, el reenvío y el que dispara el admin.
5. **El admin ve el resultado**: la respuesta de `POST /admin/usuarios/{id}/verificacion/reenviar`
   incluye en `message` "Enviamos el código a {correo}. Vence en 1 minuto." y
   `GET /admin/usuarios/{id}` expone `correo_confirmado_en_proveedor: bool` (solo lectura, para
   diagnosticar casos como este).
6. Contrato 05 (función nueva) y 04 (campo nuevo y enlace del correo).

**No incluye**
- Cambiar la regla de que el backend decide quién está verificado.
- Reactivar *Confirm email* en Supabase.
- Pantallas (HU-F-520).

## Prompt de ejecución
```text
Ejecuta HU-B-419 en SIPE-SOUND-BACKEND. Causa: una cuenta verificada por código tiene
profiles.correo_verificado_en pero auth.users.email_confirmed_at sigue nulo, y Supabase rechaza el
inicio de sesión con email_not_confirmed. Crea la revisión con la función SECURITY DEFINER
confirmar_correo_auth(uuid) (EXECUTE solo para el rol del backend) y repara los datos existentes.
Llámala en la misma transacción que marcar_verificada (verificar y verificar_manual) y en el
cambio de correo. En AuthService.iniciar_sesion, ante email_not_confirmed con perfil ya
verificado, confírmala y reintenta una vez; con perfil sin verificar mantén el aviso actual.
Agrega el botón "Confirmar mi correo" a verificar_correo.html y .txt con enlace
/verificar?email=…, sin el código. No cambies la forma de las respuestas existentes. Sin pruebas
unitarias.
```

## Pasos
1. Revisión Alembic con la función y la reparación de datos.
2. `RepositorioCuentas.confirmar_en_proveedor` y su uso en verificar / verificar manual / cambio de correo.
3. Reintento único en `AuthService.iniciar_sesion` (sin recursión; sin filtrar si la cuenta existe).
4. Plantillas del correo y `correo_confirmado_en_proveedor` en el detalle del admin.

## Criterios de aceptación
```gherkin
Escenario: Cuenta verificada con código
  Dado una cuenta nueva que el admin verifica con código
  Cuando la persona inicia sesión
  Entonces entra sin ver "aún no has confirmado tu correo"

Escenario: Cuenta afectada antes de la corrección
  Dado una cuenta con correo_verificado_en lleno y email_confirmed_at nulo
  Cuando se aplica la revisión
  Entonces la persona inicia sesión con su contraseña sin pedir nada más

Escenario: Autocuración
  Dado una cuenta verificada que Supabase aún marca sin confirmar
  Cuando inicia sesión
  Entonces el backend la confirma, repite el inicio una vez y devuelve la sesión

Escenario: Cuenta realmente pendiente
  Dado una cuenta sin verificar
  Cuando intenta iniciar sesión
  Entonces recibe el aviso con requiere_verificacion y "Pedir otro código" sí le envía un código

Escenario: Botón en el correo
  Cuando el admin envía el código de confirmación
  Entonces el correo trae el código y un botón que abre /verificar con el correo ya escrito
  Y el enlace no contiene el código
```

## Verificación manual
```bash
uv run alembic upgrade head
# Consulta de control: debe dar 0 filas
#   select 1 from public.profiles p join auth.users u on u.id = p.id
#   where p.correo_verificado_en is not null and u.email_confirmed_at is null;
curl -s -X POST localhost:8000/api/v1/auth/sesion -H "Content-Type: application/json" \
  -d '{"email":"reginopm0897@gmail.com","password":"<su contraseña>"}'   # 200
```

## Definición de hecho específica
- [ ] La consulta de control devuelve 0 filas en producción tras aplicar la revisión.
- [ ] `EXECUTE` de `confirmar_correo_auth` revocado a `public`, `anon` y `authenticated`.
- [ ] El correo se ve bien en claro y oscuro con el botón (captura en el PR).
- [ ] `check_migrations.py` en verde y `upgrade → downgrade → upgrade` probado.
