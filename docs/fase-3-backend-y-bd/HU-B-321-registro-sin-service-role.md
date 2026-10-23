# HU-B-321 · Cuentas sin la clave service_role

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-320 |
| Rama | `hu/HU-B-321-registro-sin-service-role` |
| Reemplaza | HU-B-318 (registro e invitación por la API de Supabase) |
| Origen | Decisión del equipo (2026-10-24): el backend no guarda claves de Supabase |

## Historia
**Como** equipo
**quiero** que el backend no dependa de `SUPABASE_SERVICE_ROLE_KEY`
**para** no custodiar una clave que ignora RLS ni leer variables que el `.env` ya no tiene.

## Análisis
| Uso de la clave | Alternativa sin clave |
|---|---|
| `POST /auth/registro` (signup) | El frontend usa `supabase.auth.signUp` con su clave pública. El rol lo fija el trigger (`estudiante`); los límites, el formulario (contrato 08 del frontend) y la base (0013). |
| Invitación de docentes (`/auth/v1/invite`, solo con service_role) | **Correo preautorizado**: el admin lo registra y la base asigna `docente` al confirmar el correo. |

## Alcance
1. Se retiran `SUPABASE_SERVICE_ROLE_KEY`, `FRONTEND_URL`, el cliente de Supabase Auth,
   `POST /auth/registro`, `POST /admin/docentes/invitaciones` y los errores que solo ellos usaban.
2. Revisión `0014`: tabla `docentes_preautorizados` (RLS sin políticas), función
   `aplicar_docente_preautorizado()`, trigger `on_auth_user_confirmed` y `handle_new_user()`
   que aplica la preautorización si la cuenta nace confirmada. Nunca toca a un admin.
3. `EXECUTE` revocado a `public`, `anon` y `authenticated` en las funciones (Supabase las
   expondría como RPC y un estudiante podría darse el rol docente).
4. Endpoints admin: `POST`, `GET` y `DELETE /admin/docentes/preautorizaciones`.

## Seguridad
- El rol se asigna al **confirmar** el correo: registrarse con un correo ajeno no basta.
  Requiere *Confirm email* activado en Supabase (valor por defecto).
- Cambiar el correo de una cuenta ya confirmada no dispara el trigger.

## Criterios de aceptación
```gherkin
Escenario: Docente preautorizado
  Dado que el admin preautoriza "profe@colegio.edu.co"
  Cuando esa persona se registra y confirma su correo
  Entonces su rol es docente

Escenario: Sin confirmar no hay rol
  Dado un correo preautorizado
  Cuando alguien se registra con él y no confirma
  Entonces su rol sigue siendo estudiante

Escenario: Sin RPC
  Cuando el rol anon ejecuta aplicar_docente_preautorizado
  Entonces PostgreSQL responde permiso denegado

Escenario: Configuración
  Dado un .env sin SUPABASE_SERVICE_ROLE_KEY ni FRONTEND_URL
  Entonces la app arranca y ningún endpoint las necesita
```
