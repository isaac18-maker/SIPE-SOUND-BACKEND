# HU-B-318 · Registro de estudiantes e invitación de docentes

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-304, HU-B-317 |
| Rama | `hu/HU-B-318-registro` |
| Origen | Solicitud del equipo (2026-10-23) |

## Historia
**Como** estudiante quiero crear mi cuenta desde la plataforma; **como** administrador
quiero invitar a los docentes por correo, **para** que cada persona entre con el rol correcto
sin que nadie pueda asignarse permisos que no le corresponden.

## Análisis: ¿registro directo o no?

| Rol | Vía | Por qué |
|---|---|---|
| Estudiante | **Directo**: `POST /api/v1/auth/registro` | Bajo riesgo; el perfil nace como `estudiante` (trigger). Correo de confirmación obligatorio. |
| Docente | **Indirecto**: invitación de un admin (`POST /api/v1/admin/docentes/invitaciones`) | Un docente ve datos de menores: nadie puede declararse docente por su cuenta. |
| Administrador | **Nunca por la API**: `scripts.promover_admin` (el primero) o `PATCH /admin/usuarios/{id}/rol` (otro admin) | Máximo privilegio. |

## Decisiones
- El registro **no revela** si un correo ya existe (misma respuesta 201): evita enumerar cuentas de estudiantes.
- Contraseña: 8–72 caracteres con letras y números; aceptación de términos obligatoria; campos extra rechazados (no se puede enviar `rol`).
- Límite: 20 registros por hora por IP (los colegios comparten IP).
- Requiere `SUPABASE_SERVICE_ROLE_KEY` (solo servidor) y `FRONTEND_URL`. Sin la clave, 503.
- Cliente HTTP con la librería estándar (sin `requests`); solo HTTPS; nunca registra contraseñas ni claves.

## Configuración en Supabase (una vez)
1. Authentication → URL Configuration → *Redirect URLs*: agregar `<FRONTEND_URL>/login` y `<FRONTEND_URL>/activar-cuenta`.
2. Authentication → Emails → SMTP Settings: SMTP propio (el incluido envía muy pocos correos por hora).
3. Plantilla "Invite user": texto en español.

## Criterios de aceptación
```gherkin
Escenario: Registro de estudiante
  Cuando envio nombre, correo, contrasena segura y acepto terminos
  Entonces recibo 201 "Te enviamos un correo para confirmar tu cuenta."
  Y al confirmar, mi perfil tiene rol estudiante

Escenario: No auto-asignarse rol
  Cuando envio ademas "rol": "admin"
  Entonces recibo 400 "rol: Este campo no está permitido."

Escenario: Invitacion de docente
  Dado un administrador
  Cuando invita a luis@colegio.edu.co
  Entonces Luis recibe el correo y al entrar su rol es docente
```
