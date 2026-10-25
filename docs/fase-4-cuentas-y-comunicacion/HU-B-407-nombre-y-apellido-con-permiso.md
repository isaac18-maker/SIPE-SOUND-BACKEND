# HU-B-407 · Nombre y apellido editables solo con permiso del administrador

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Should |
| Estimación | 3 puntos |
| Depende de | HU-B-402 |
| Rama | `hu/HU-B-407-nombre-y-apellido` |
| Relacionada | HU-F-403 (Mi cuenta), HU-F-404 (permiso en el panel) |

## Historia
**Como** administrador
**quiero** decidir, persona por persona, quién puede cambiar su nombre y apellido
**para** que los listados del docente coincidan con los registros del colegio y nadie se cambie el nombre por juego.

## Contexto
- `profiles.nombre` (2–80) es el único campo de nombre; lo llena `handle_new_user()` desde el registro.
- No hay `apellido` ni forma de editar el nombre después del registro.
- `POST /auth/registro` recibe `nombre` (`app/schemas/auth.py`, `RegistroIn`).

## Decisión
- Permiso **por usuario** (`puede_editar_nombre`, por defecto `false`). El admin lo activa o lo
  desactiva; no se apaga solo después de un cambio (si el colegio quiere un solo cambio, el admin
  lo desactiva después).
- El apellido es obligatorio en registros nuevos y opcional (`null`) para las cuentas existentes.

## Alcance
**Incluye**
1. Revisión `0023_apellido_y_permiso_nombre` (esquema; el número se recalculó al implementar):
   - `profiles.apellido text null` con los CHECK del nombre (2–80, sin caracteres de control).
   - `profiles.puede_editar_nombre boolean not null default false`.
   - `handle_new_user()` copia y normaliza `raw_user_meta_data->>'apellido'` igual que el nombre
     (si no viene o no cumple, `null`).
2. `RegistroIn` agrega `apellido` (mismas reglas que `nombre`) y lo envía a Supabase en `data`.
   **Opcional por ahora** (contrato 07: el backend se despliega primero y no rompe al frontend
   vigente, cuyo formulario no envía apellido); pasa a obligatorio cuando HU-F-403 lo incluya.
3. `GET /me` agrega `apellido` y `puede_editar_nombre`.
4. `PATCH /me` 🎓🧑‍🏫🛡️: `{nombre?, apellido?}` → 403 "El administrador no ha habilitado el cambio de
   nombre en tu cuenta." si `puede_editar_nombre` es `false` (los admins siempre pueden).
   `extra="forbid"`: `rol`, `nivel` o cualquier otro campo → 400.
5. Admin (`@roles_required("admin")`):
   - `PATCH /admin/usuarios/{id}/permisos` `{puede_editar_nombre: bool}`.
   - `POST /admin/usuarios/permisos` `{usuario_ids: [...] (1–100), puede_editar_nombre: bool}` →
     `{actualizados: N}`. Ids inexistentes se ignoran y se informan en `meta.no_encontrados`.
   - Ambos escriben en el log de la aplicación (admin, valor y cuántas cuentas). **No** pueden
     registrar `permiso_nombre` en `acciones_admin` porque esa tabla la crea HU-B-405, que depende
     de esta: HU-B-405 agrega ese registro.
6. `GET /admin/usuarios` (HU-B-405) incluye `apellido` y `puede_editar_nombre`, con filtro
   `?puede_editar_nombre=`.
7. Listados del docente (`EstudianteCursoOut`) agregan `apellido`.
8. Contrato 04 §4.1.1, §4.4, §5, §7 (`apellido`).

**No incluye**
- Pantallas (HU-F-403, HU-F-404).
- Historial de nombres anteriores (queda en `acciones_admin` solo el cambio de permiso; el cambio
  de nombre en sí se registra en el log de aplicación sin el valor).

## Prompt de ejecución
```text
Ejecuta HU-B-407 en SIPE-SOUND-BACKEND. Agrega profiles.apellido (2–80, mismas reglas que nombre,
null en cuentas viejas) y profiles.puede_editar_nombre (false por defecto) en la revisión 0024;
handle_new_user copia el apellido del registro. PATCH /me solo acepta nombre y apellido y responde
403 si el admin no lo habilitó. El admin activa el permiso por usuario o en lote (máx. 100) y cada
cambio queda en acciones_admin. Los límites van a app/core/longitudes.py, a la base y al contrato
§7 (los tres a la vez).
```

## Pasos
1. Revisión 0024 con `downgrade()`.
2. Esquemas (`RegistroIn`, `PerfilEditarIn`, permisos) y límites.
3. `PerfilService.editar` y servicio de permisos.
4. Rutas y contratos.

## Criterios de aceptación
```gherkin
Escenario: Sin permiso
  Dado que el admin no habilitó mi cambio de nombre
  Cuando envío PATCH /me con {"nombre":"Ana María"}
  Entonces recibo 403 y mi nombre no cambia

Escenario: Con permiso
  Dado que el admin habilitó mi permiso
  Cuando envío PATCH /me con {"nombre":"Ana María","apellido":"Gómez"}
  Entonces recibo 200 y GET /me los muestra

Escenario: Campo extra
  Cuando envío PATCH /me con {"rol":"admin"}
  Entonces recibo 400 VALIDACION

Escenario: Permiso en lote
  Cuando el admin habilita el permiso para 30 estudiantes a la vez
  Entonces recibo {"actualizados": 30} y 30 acciones en acciones_admin

Escenario: Registro con apellido
  Cuando me registro con nombre "Ana" y apellido "Gómez"
  Entonces mi perfil tiene ambos
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
curl -s -X PATCH localhost:5000/api/v1/me -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"nombre":"Ana María"}'
```

## Definición de hecho específica
- [ ] Límite de `apellido` igual en `longitudes.py`, CHECK y contrato §7 (y PR enlazado en el frontend).
- [ ] Cuentas existentes siguen funcionando con `apellido = null`.
