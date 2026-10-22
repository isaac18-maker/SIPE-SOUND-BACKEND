# HU-B-304 · Agregar roles (estudiante, docente, admin) y autorización

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-303, HU-B-205 |
| Rama | `hu/HU-B-304-roles` |

## Historia
**Como** administrador de la plataforma
**quiero** asignar el rol de docente a ciertas cuentas
**para** que solo ellas accedan al panel docente.

## Alcance
**Incluye**
- Revisión `0002`: `profiles.rol` (`text not null default 'estudiante'`, CHECK), `profiles.actualizado_en`, función genérica `public.tocar_actualizado_en()` y su trigger en `profiles`.
- `roles_required(*roles)` funcional en `core/security.py`: carga el rol desde `profiles` (caché por petición en `g`).
- `CurrentUser.rol`.
- `GET /api/v1/me` → `{ id, nombre, email, rol, nivel }`.
- `PATCH /api/v1/admin/usuarios/{id}/rol` (solo admin).
- Script `scripts/promover_admin.py <email>` para el primer administrador (solo `APP_ENV=local|staging` o con confirmación).

**No incluye**: instituciones ni permisos granulares.

## Prompt de ejecución
```text
Ejecuta HU-B-304 en SIPE-SOUND-BACKEND.
- Crea la revisión 0002 (tipo esquema) con autogenerate y complétala con op.execute
  para la función tocar_actualizado_en() y el trigger. Downgrade real.
- El rol NO se lee del JWT (los metadatos del usuario los puede editar él mismo
  desde el cliente). Se lee de profiles en cada petición autenticada.
- roles_required lanza SinPermiso (403) si el rol no está permitido.
- Evita que un admin se quite a sí mismo el rol admin si es el único (409).
```

## Criterios de aceptación
```gherkin
Escenario: Rol por defecto
  Dado un usuario recién registrado
  Cuando consulto GET /api/v1/me
  Entonces rol es "estudiante"

Escenario: Acceso denegado al panel
  Dado un estudiante autenticado
  Cuando consulto GET /api/v1/docente/resumen
  Entonces recibo 403 SIN_PERMISO

Escenario: El usuario no puede auto-promoverse
  Dado un estudiante que modifica su user_metadata con rol "docente"
  Cuando consulto GET /api/v1/me
  Entonces rol sigue siendo "estudiante"
```

## Verificación manual
```bash
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
uv run python scripts/promover_admin.py yo@correo.test
curl -s -H "Authorization: Bearer $TOKEN" localhost:5000/api/v1/me
```

## Definición de hecho específica
- [ ] Un usuario no puede cambiar su propio `rol` usando la `anon key` (la política RLS "Editar propio perfil" sigue permitiendo el UPDATE de la fila). En la revisión `0002`, con `op.execute`:
  ```sql
  revoke update on public.profiles from authenticated;
  grant update (nombre, nivel) on public.profiles to authenticated;
  ```
  y en `downgrade()` restaurar `grant update on public.profiles to authenticated;`.
