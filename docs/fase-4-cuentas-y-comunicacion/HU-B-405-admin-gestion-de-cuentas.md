# HU-B-405 · Administración: gestionar las cuentas de estudiantes y docentes

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-402, HU-B-407 |
| Rama | `hu/HU-B-405-admin-cuentas` |
| Relacionada | HU-F-404 |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §3 |

## Historia
**Como** administrador
**quiero** ver todas las cuentas con su estado, reenviar el código a quien no lo recibió, suspender y eliminar cuentas
**para** que cada estudiante y docente pueda entrar a tiempo y retirar a quien ya no debe tener acceso.

## Contexto
- El admin solo tiene `PATCH /admin/usuarios/{id}/rol` y las preautorizaciones de docentes
  (`app/api/v1/admin.py`). No puede listar cuentas ni ver si alguien quedó sin verificar.
- B-401 registra cada envío en `envios_correo`; B-402 creó `correo_verificado_en` y `CodigoService`.

## Alcance
**Incluye** (prefijo `/api/v1/admin`, `@roles_required("admin")`)

| Endpoint | Detalle |
|---|---|
| `GET /usuarios` | Paginado. Filtros `?rol=&estado=pendiente_verificacion\|activa\|suspendida&q=` (nombre o correo, máx. 80) y orden `?orden=nombre\|-creado_en\|-ultimo_acceso`. Cada fila: `id`, `nombre`, `apellido` (B-407), `email` (completo: el admin lo necesita), `rol`, `estado`, `creado_en`, `ultimo_acceso` (`auth.users.last_sign_in_at`), `ultimo_envio_verificacion` (`{estado, creado_en}` o `null`), `cursos` (inscripciones activas; para docentes, cursos a cargo). `meta.totales` por estado. |
| `GET /usuarios/{id}` | Lo anterior + inscripciones (`curso_id`, `curso`, `docente`, `inscrito_en`), cursos a cargo, resumen de progreso (`/progreso/resumen` del estudiante) y las últimas 20 `acciones_admin` sobre la cuenta. |
| `POST /usuarios/{id}/verificacion/reenviar` | Emite un código nuevo y envía `verificar_correo`. 409 si ya está verificada. 429 si hubo un envío hace menos de 1 minuto. Responde el `estado` del envío (se consulta tras unos segundos con `GET /usuarios/{id}`). |
| `POST /usuarios/{id}/verificacion` | Verificación **manual** (aulas donde el estudiante no tiene acceso a su correo). Cuerpo `{motivo}` 10–300. Llena `correo_verificado_en` (dispara la preautorización de docente) e invalida el código abierto. |
| `PATCH /usuarios/{id}/estado` | `{estado: "suspendida", motivo}` (motivo 10–300) o `{estado: "activa"}`. Suspender cierra todas sus sesiones (`cerrar_sesiones`). |
| `DELETE /usuarios/{id}` | Cuerpo `{confirmacion: "<correo de la cuenta>"}`. Borra la cuenta y, por cascada, perfil, progreso, intentos e inscripciones. 409 si es docente con cursos a cargo ("Reasigna sus cursos a cargo (N) antes de eliminar la cuenta.", B-406). 403 si es admin o es el propio usuario. |

1. Revisión `0023_suspension_y_auditoria` (esquema):
   - `profiles.suspendido_en timestamptz null`, `profiles.motivo_suspension text null` (10–300),
     CHECK de coherencia (`(suspendido_en is null) = (motivo_suspension is null)`).
   - `acciones_admin`: `id uuid`, `admin_id` (FK `profiles` SET NULL), `usuario_id uuid` (sin FK: la
     auditoría sobrevive a la cuenta borrada), `accion` (`reenviar_verificacion`, `verificar_manual`,
     `suspender`, `reactivar`, `eliminar`, `cambiar_rol`, `revocar_curso`, `reasignar_curso`,
     `permiso_nombre`), `detalle jsonb` (sin contraseñas ni códigos; al eliminar guarda el correo
     enmascarado), `creado_en`. Índice `(usuario_id, creado_en desc)`. RLS sin políticas.
   - `public.eliminar_cuenta(p_usuario uuid)` `SECURITY DEFINER`: se niega con un admin; `delete from
     auth.users where id = p_usuario` (`profiles` cae por cascada). `EXECUTE` revocado a `public`,
     `anon`, `authenticated`. La línea del `delete` lleva `# destructivo-aprobado: HU-B-405`
     (lo exige `check_migrations.py` al estar dentro de un `op.execute`).
2. Estado `suspendida` en el proveedor de estado de `auth_required` (B-402) y en `POST /auth/sesion`
   → 403 "Tu cuenta está suspendida. Habla con el administrador."
3. `PATCH /usuarios/{id}/rol` (existente) registra `cambiar_rol` en `acciones_admin`.
4. `AdminUsuariosService` + `SqlAdminUsuariosRepository` (una consulta para el listado, con
   `count(*) over ()`, como `SqlSeguimientoRepository`).
5. Contrato 04 §4.4 y §7; contrato 05 (tabla ON DELETE y regla de borrado de cuentas).

**No incluye**
- Cursos de docentes, reasignación y revocar inscripciones (B-406).
- Permiso para editar el nombre (B-407).
- Crear cuentas desde el panel (el registro y las preautorizaciones siguen igual).
- Exportar el listado.

## Regla de borrado (derecho de supresión, Ley 1581 de 2012)
El borrado es **físico** y no se puede deshacer: el frontend pide escribir el correo. Los
comentarios que la persona escribió como docente quedan con `docente_id = null` (contrato 05).
La auditoría conserva solo el correo enmascarado y el id.

## Prompt de ejecución
```text
Ejecuta HU-B-405 en SIPE-SOUND-BACKEND. Agrega la gestión de cuentas del admin: listado con
estado calculado (pendiente_verificacion, activa, suspendida), detalle, reenviar código,
verificación manual con motivo, suspender/reactivar (cierra sesiones) y eliminar con
confirmación del correo mediante public.eliminar_cuenta (SECURITY DEFINER, EXECUTE revocado,
nunca un admin). Toda acción queda en acciones_admin sin datos sensibles. Suspendida = 403 en
inicio de sesión y en auth_required. Capas: api → services → repositories. Sin dependencias.
```

## Pasos
1. Revisión 0023 con `downgrade()`; `check_migrations.py` en verde.
2. Modelos y repositorio; listado en una sentencia.
3. Servicio con reglas (no admin, no a sí mismo, 409 docente con cursos) y auditoría.
4. Rutas y estado `suspendida` en la puerta de entrada.
5. Contratos 04 y 05.

## Criterios de aceptación
```gherkin
Escenario: Ver quién no ha verificado
  Cuando pido GET /admin/usuarios?estado=pendiente_verificacion
  Entonces veo cada cuenta con su último envío ("enviado" o "fallido") y la fecha

Escenario: Reenviar a quien no le llegó
  Dado una cuenta pendiente cuyo último envío está "fallido"
  Cuando envío POST /admin/usuarios/{id}/verificacion/reenviar
  Entonces se emite un código nuevo, el anterior deja de servir
  Y acciones_admin registra "reenviar_verificacion"

Escenario: Suspender
  Dado un estudiante con sesión abierta
  Cuando lo suspendo con un motivo
  Entonces su siguiente petición a la API responde 403
  Y no puede iniciar sesión

Escenario: Eliminar
  Cuando elimino un estudiante enviando su correo como confirmación
  Entonces su cuenta, progreso e inscripciones desaparecen
  Y acciones_admin conserva la acción con el correo enmascarado

Escenario: Docente con cursos
  Cuando intento eliminar a un docente con 2 cursos a cargo
  Entonces recibo 409 "Reasigna sus cursos a cargo (2) antes de eliminar la cuenta."

Escenario: Protección de admins
  Cuando intento suspender o eliminar a otro admin o a mí mismo
  Entonces recibo 403
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
curl -s "localhost:5000/api/v1/admin/usuarios?estado=pendiente_verificacion" -H "Authorization: Bearer $TOKEN_ADMIN"
```

## Definición de hecho específica
- [ ] El listado de 200 cuentas responde en una sola sentencia SQL (medición en el PR).
- [ ] `detalle` de `acciones_admin` nunca contiene contraseñas, códigos ni el correo completo de una cuenta eliminada.
- [ ] `eliminar_cuenta` no se puede ejecutar como `anon` ni `authenticated`.
