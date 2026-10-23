# HU-B-322 · Autenticación a través del backend

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-321 |
| Rama | `hu/HU-B-322-autenticacion-por-backend` |
| Relacionada | HU-F-207 (frontend: retirar Supabase) |
| Origen | Decisión del equipo (2026-10-22): el backend es el único que habla con Supabase |

## Historia
**Como** equipo
**quiero** que registro, inicio, renovación y cierre de sesión pasen por la API
**para** que el frontend no dependa de Supabase, los límites de los campos se apliquen
también en la API y la identidad tenga un único punto de control.

## Contexto
- Desde HU-B-321 el frontend llamaba a `supabase.auth.signUp` / `signInWithPassword` con la
  *anon key* y el backend solo validaba el JWT.
- El navegador guardaba **ambos** tokens en `localStorage` (comportamiento de `supabase-js`):
  un XSS podía robar el *refresh token* y mantener la sesión indefinidamente.
- Los límites de nombre, correo y contraseña solo los aplicaban el formulario y Supabase.

## Decisión
| Tema | Decisión | Por qué |
|---|---|---|
| Clave | `SUPABASE_ANON_KEY` (pública) en el backend | Basta para `signup`, `token` y `logout`. **No** se vuelve a la *service_role* (HU-B-321). |
| Access token | En el cuerpo; el frontend lo guarda en memoria y lo envía como `Bearer` | `auth_required` y todas las rutas protegidas quedan igual. |
| Refresh token | Cookie `sipe_refresh` `HttpOnly`, `Path=/api/v1/auth`, 30 días, rotada en cada renovación | JavaScript no puede leerla; solo acompaña a `/auth/*`. |
| CSRF | `renovar` y `DELETE /auth/sesion` exigen JSON; CORS con orígenes explícitos y `supports_credentials` | Un sitio ajeno no puede enviar JSON con la cookie sin *preflight*, y CORS lo rechaza. |
| Rol | Sigue saliendo de `profiles` (`GET /me`) | El rol nunca se lee del token (HU-B-304). |
| Dependencias | Ninguna nueva (`urllib`) | Igual que el cliente retirado en HU-B-321. |

## Alcance
**Incluye**
1. `app/infrastructure/supabase_auth.py`: `registrar`, `iniciar_sesion`, `refrescar`,
   `cerrar_sesion`; traduce los errores de Supabase a la respuesta estándar en español.
2. `app/schemas/auth.py`: `RegistroIn` (nombre 2–80 con patrón, correo, contraseña 8–72 con
   letras y números) e `InicioSesionIn` (contraseña 1–72). `extra="forbid"`.
3. `app/services/auth_service.py` y `app/api/v1/auth.py`: rutas del contrato 4.1.1.
4. Configuración: `SUPABASE_ANON_KEY` (opcional; sin ella `/auth/*` → 503),
   `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, con validaciones que impiden arrancar con
   una cookie insegura fuera de local.
5. Errores `DemasiadasSolicitudes` (429) y `ServicioNoDisponible` (503).
6. CORS con `supports_credentials=True`.
7. `.env.example`, `docs/configuracion-entornos.md`, contrato 02 y 04.

**No incluye**
- Recuperar contraseña ni cambiar correo (nueva HU si se necesitan).
- `acepta_terminos` en `RegistroIn`: el formulario aún no tiene la casilla (HU-F-313). Cuando
  exista, se agrega al esquema como `Literal[True]`.
- Limitador compartido entre procesos (Redis): sigue en memoria (ver `app/core/limites.py`).

## Prompt de ejecución
```text
Ejecuta HU-B-322 en SIPE-SOUND-BACKEND. El backend pasa a ser el único cliente de
Supabase Auth usando SUPABASE_ANON_KEY (nunca service_role). Implementa
POST /auth/registro, POST /auth/sesion, POST /auth/sesion/renovar y DELETE /auth/sesion
según el contrato 04 §4.1.1. El refresh token solo viaja en la cookie httpOnly
sipe_refresh; el access token en el cuerpo. Sin dependencias nuevas. Nunca registres
contraseñas, tokens ni la clave. Documenta cada variable nueva en .env.example y en
docs/configuracion-entornos.md.
```

## Configuración necesaria
| Dónde | Qué |
|---|---|
| `.env` del backend | `SUPABASE_ANON_KEY=<anon o publishable key>` (Supabase → Project Settings → API Keys). Opcionales: `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`. |
| `.env` del backend | `CORS_ORIGINS` con el origen **exacto** del frontend (las cookies no viajan a otros orígenes). |
| Supabase → Authentication → URL Configuration | **Site URL** = `<url-del-frontend>/login` (enlace del correo de confirmación). |
| Supabase → Authentication → Providers → Email | *Confirm email* activado; contraseña mínima 8 con letras y dígitos. |
| Supabase → Data API | RLS activado en todas las tablas de `public` (o `public` fuera de *Exposed schemas*). |
| Despliegue | Si frontend y API quedan en dominios distintos: `AUTH_COOKIE_SAMESITE=None` y HTTPS en ambos. |

## Criterios de aceptación
```gherkin
Escenario: Inicio de sesión
  Dado una cuenta confirmada
  Cuando envío POST /auth/sesion con correo y contraseña correctos
  Entonces recibo 200 con access_token y usuario
  Y la respuesta trae la cookie sipe_refresh HttpOnly con Path=/api/v1/auth
  Y el cuerpo no contiene el refresh token

Escenario: Credenciales incorrectas
  Cuando envío una contraseña equivocada
  Entonces recibo 401 NO_AUTENTICADO con "El correo o la contraseña no coinciden…"

Escenario: Renovación con rotación
  Dado que inicié sesión
  Cuando envío POST /auth/sesion/renovar con {} y la cookie
  Entonces recibo un access_token nuevo y una cookie sipe_refresh nueva

Escenario: CSRF
  Cuando envío POST /auth/sesion/renovar con Content-Type text/plain
  Entonces recibo 400 VALIDACION y no se renueva nada

Escenario: Cierre de sesión
  Cuando envío DELETE /auth/sesion con {} y mi Bearer
  Entonces recibo 200, la cookie se borra y el refresh token queda revocado en Supabase

Escenario: Sin clave configurada
  Dado un .env sin SUPABASE_ANON_KEY
  Entonces la app arranca y POST /auth/sesion responde 503 "falta configurar SUPABASE_ANON_KEY"

Escenario: Cookie insegura en producción
  Dado APP_ENV=production y AUTH_COOKIE_SECURE=0
  Entonces la app no arranca y el error nombra AUTH_COOKIE_SECURE
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python -c "from app import create_app; create_app(); print('configuracion OK')"
curl -i -X POST http://localhost:5000/api/v1/auth/sesion \
  -H "Content-Type: application/json" -d '{"email":"tu@correo.co","password":"..."}'
```

## Definición de hecho específica
- [ ] Ningún log contiene contraseñas, tokens ni `SUPABASE_ANON_KEY`.
- [ ] `grep -rn "service_role" app` sin resultados.
- [ ] HU-F-207 desplegada después de esta HU (orden de merge: backend primero).
