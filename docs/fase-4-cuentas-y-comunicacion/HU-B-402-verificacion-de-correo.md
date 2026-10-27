# HU-B-402 · Verificar el correo con un código propio de un solo uso

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-401, HU-B-321, HU-B-322 |
| Rama | `hu/HU-B-402-verificacion-de-correo` |
| Relacionada | HU-F-401 (pantalla del código) |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §2, §3, §4.1, §5 |

## Historia
**Como** persona que se registra
**quiero** recibir un código de 6 dígitos en mi correo y escribirlo en la página
**para** activar mi cuenta sin depender de un enlace que puede vencer o abrirse en otro dispositivo.

## Contexto
- `POST /auth/registro` (`app/services/auth_service.py`) llama a Supabase `signup`; Supabase envía su
  correo de confirmación y `POST /auth/sesion` responde 422 si el correo no está confirmado.
- La revisión 0014 asigna el rol docente preautorizado con el trigger `on_auth_user_confirmed`
  (sobre `auth.users.email_confirmed_at`) y desde `handle_new_user()` si la cuenta nace confirmada.
- `auth_required` (`app/core/security.py`) solo valida el JWT: no mira el estado de la cuenta.

## Alcance
**Incluye**
1. Revisión `0019_verificacion_de_correo` (esquema):
   - `profiles.correo_verificado_en timestamptz null`.
   - Tabla `codigos_verificacion` (00-decisiones §4.1) con su índice único parcial y RLS sin políticas.
   - `public.handle_profile_verificado()` + trigger `on_profile_verificado`
     (`after update of correo_verificado_en on public.profiles … when old is null and new is not null`)
     que llama a `aplicar_docente_preautorizado(new.id, <correo de auth.users>)`.
   - `handle_new_user()` **sin** la rama `if new.email_confirmed_at is not null` (vuelve al cuerpo de 0013).
   - `drop trigger on_auth_user_confirmed` y `drop function handle_user_confirmed()`
     con `# destructivo-aprobado: HU-B-402` (no borra datos; quita lógica que se vuelve insegura).
   - `EXECUTE` revocado a `public`, `anon`, `authenticated` en las funciones nuevas.
   - `downgrade()` restaura el trigger y las funciones de 0014.
2. Revisión `0020_copiar_correos_confirmados` (datos, idempotente):
   `update profiles set correo_verificado_en = u.email_confirmed_at from auth.users u where … and correo_verificado_en is null`.
3. `app/services/codigo_service.py`: `emitir(usuario_id, proposito, email_destino)` (invalida el
   abierto, genera 6 dígitos con `secrets.randbelow`, guarda el HMAC con `CODIGOS_SECRETO`) y
   `consumir(usuario_id, proposito, codigo)` (compara con `hmac.compare_digest`, suma intentos, a los
   5 invalida, y consume con `UPDATE … RETURNING` atómico). Reutilizable por B-403 y B-404.
4. Flujo de registro:
   - `POST /auth/registro`: después del `signup`, si la cuenta es nueva y no está verificada, emite
     el código y envía `verificar_correo`. **La respuesta no cambia** (misma forma exista o no el correo).
   - `POST /auth/verificacion` 🌐 (10/min por IP): `{email, codigo}` → 200 `{email, verificado: true}`.
     Código incorrecto, vencido, usado o correo inexistente → **el mismo** 422 `REGLA_NEGOCIO`
     "El código no es válido o ya venció. Pide uno nuevo." (no revela qué cuentas existen).
   - `POST /auth/verificacion/reenviar` 🌐 (5/h por IP y 1 por minuto por correo): `{email}` →
     siempre 200 "Si el correo tiene una cuenta pendiente, te enviamos un código nuevo."
5. Puerta de entrada:
   - `POST /auth/sesion`: si Supabase entrega sesión pero `correo_verificado_en` es nulo, el backend
     **revoca** esa sesión (`logout`) y responde el 422 actual ("Aún no confirmas tu correo…") con
     `meta: {"requiere_verificacion": true}`.
   - `auth_required` y `usuario_opcional`: un proveedor inyectado (`configurar_proveedor_estado`,
     igual que el de rol) devuelve el estado de la cuenta; `pendiente_verificacion` → 403
     `SIN_PERMISO` "Confirma tu correo para continuar." Una sola consulta por PK; se mide en el PR.
6. `CODIGOS_SECRETO` en configuración (`SecretStr`, ≥ 32 caracteres; sin ella la app no arranca).
7. Contrato 04 (§4.1.1, tabla de roles y §7: `codigo` = 6 dígitos), contrato 05 (tabla ON DELETE:
   `profiles → codigos_verificacion` CASCADE), `docs/configuracion-entornos.md` (paso de Supabase).

**No incluye**
- Restablecer contraseña (B-403) ni cambiar correo (B-404).
- Reenvío desde el panel del admin (B-405).
- Pantallas (HU-F-401).

## Seguridad
| Amenaza | Defensa |
|---|---|
| Adivinar el código (10⁶ combinaciones) | 5 intentos por código, 10/min por IP, código nuevo invalida el anterior. |
| Reutilizar un código | `UPDATE … WHERE usado_en IS NULL AND invalidado_en IS NULL AND expira_en > now() RETURNING`; dos peticiones simultáneas: solo una recibe fila. |
| Robo de la tabla | Solo hay HMAC con un secreto que no está en la base. |
| Enumerar cuentas | Registro, verificación y reenvío responden igual exista o no el correo. |
| Token directo de Supabase con cuenta sin verificar | `auth_required` revisa `correo_verificado_en`. |
| Docente preautorizado por registro con correo ajeno | El rol se aplica al verificar **nuestro** código (trigger sobre `profiles`). |

## Prompt de ejecución
```text
Ejecuta HU-B-402 en SIPE-SOUND-BACKEND. El backend pasa a ser dueño de la verificación de correo:
profiles.correo_verificado_en + tabla codigos_verificacion (solo HMAC, 15 min, un solo uso,
5 intentos). En la MISMA revisión 0019 mueve la asignación del docente preautorizado al trigger
on_profile_verificado y retira on_auth_user_confirmed (marca destructivo-aprobado: HU-B-402);
si no, desactivar "Confirm email" en Supabase daría el rol docente a cualquiera. La revisión
0020 copia los correos ya confirmados. Registro, verificación y reenvío responden igual exista
o no el correo. auth_required rechaza cuentas sin verificar. Nunca registres códigos, tokens ni
contraseñas en logs. No cambies la forma de las respuestas existentes de /auth/*.
```

## Pasos
1. Revisión 0019 (con `downgrade()` real) y 0020; `check_migrations.py` en verde.
2. Modelos `CodigoVerificacion` y columna en `Profile`; repositorio.
3. `CodigoService` (emitir, consumir) y límites en `app/core/limites.py`.
4. Rutas `POST /auth/verificacion` y `/auth/verificacion/reenviar`; cambio en registro e inicio.
5. Proveedor de estado en `auth_required` y `usuario_opcional`.
6. Contratos y configuración.

## Criterios de aceptación
```gherkin
Escenario: Registro con código
  Dado que me registro con un correo nuevo
  Entonces recibo un correo "Tu código de SIPE-SOUND: NNNNNN"
  Cuando envío POST /auth/verificacion con ese código antes de 15 minutos
  Entonces recibo 200 y puedo iniciar sesión

Escenario: Código de un solo uso
  Dado que ya verifiqué mi correo con un código
  Cuando envío el mismo código otra vez
  Entonces recibo 422 "El código no es válido o ya venció. Pide uno nuevo."

Escenario: Código vencido
  Dado un código emitido hace 16 minutos
  Cuando lo envío
  Entonces recibo 422 y mi cuenta sigue pendiente

Escenario: Reenvío invalida el anterior
  Dado que pedí un código y luego otro
  Cuando envío el primero
  Entonces recibo 422 y el segundo sigue sirviendo

Escenario: Intentos agotados
  Cuando envío 5 códigos equivocados
  Entonces el código vigente deja de servir aunque luego escriba el correcto

Escenario: Sin verificar no hay sesión
  Dado una cuenta sin verificar con la contraseña correcta
  Cuando envío POST /auth/sesion
  Entonces recibo 422 con meta.requiere_verificacion = true y ninguna cookie sipe_refresh

Escenario: Token directo de Supabase
  Dado un access token emitido por Supabase para una cuenta sin verificar
  Cuando llamo GET /me con ese token
  Entonces recibo 403 "Confirma tu correo para continuar."

Escenario: Docente preautorizado
  Dado un correo preautorizado como docente
  Cuando la persona se registra y verifica el código
  Entonces su rol es docente
  Y si no verifica, su rol sigue siendo estudiante

Escenario: Cuentas existentes
  Dado una cuenta confirmada antes de esta HU
  Cuando se aplica la revisión 0020
  Entonces puede iniciar sesión sin pedir código
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -2 && uv run alembic upgrade head
# Con CORREO_MODO=archivo: registrarse, leer el código del .eml, verificar e iniciar sesión.
curl -s -X POST localhost:5000/api/v1/auth/verificacion -H "Content-Type: application/json" \
  -d '{"email":"nuevo@correo.co","codigo":"123456"}'
# SQL de comprobación (local): no quedan triggers sobre auth.users que asignen roles.
```

## Configuración necesaria
| Dónde | Qué |
|---|---|
| `.env` | `CODIGOS_SECRETO` (p. ej. `python -c "import secrets; print(secrets.token_urlsafe(48))"`). |
| Supabase → Authentication → Providers → Email | **Desactivar** *Confirm email* al desplegar esta HU (00-decisiones §5), nunca antes. |

## Definición de hecho específica
- [ ] `select tgname from pg_trigger where tgrelid = 'auth.users'::regclass` ya no lista `on_auth_user_confirmed`.
- [ ] Ningún log contiene códigos (revisar con `grep -rn "codigo" app | grep logger`).
- [ ] Medición en el PR del costo de la consulta de estado en `auth_required`.
- [ ] HU-F-401 se despliega después (orden de merge: backend primero).
