# HU-B-521 · Edición de cuentas, avisos por correo y acciones en lote

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Should |
| Estimación | 5 puntos |
| Depende de | HU-B-405, HU-B-406, HU-B-418 |
| Rama | `hu/HU-B-521-rediseno-admin-usuarios-cuenta-docentes` |

## Historia
**Como** administrador
**quiero** editar los datos de una cuenta, avisar por correo de un cambio de rol o de una suspensión, y actuar sobre varias cuentas a la vez
**para** gestionar un aula sin repetir la misma acción cuenta por cuenta.

## Alcance
**Incluye**
1. `PATCH /admin/usuarios/{id}` `{nombre, apellido, email}` (los tres obligatorios). Un correo nuevo
   valida formato y unicidad, deja la cuenta **pendiente** y envía un código. El administrador no
   cambia así su propio correo (403: lo hace en Mi cuenta).
2. `PATCH /admin/usuarios/{id}/rol` y `/estado` aceptan `notificar` (bool): envían los correos
   `rol_cambiado` y `cuenta_suspendida`. El motivo de la suspensión pasa a ser opcional (por
   defecto «Suspendida por un administrador.»); el de la verificación manual también.
3. `POST /admin/usuarios/lote` `{ids (≤100), accion: rol|activar|suspender|reenviar, rol?, notificar?}`
   → `{cambiadas, omitidas: [{id, motivo}]}`. Procesa solo las cuentas válidas: omite la propia y las
   que ya están en ese estado.
4. Reglas: nadie cambia su **propio** rol (403); al promover a administrador se fija
   `puede_editar_nombre = true` y al bajar de administrador `false`; `puede_editar_nombre` de un
   administrador siempre se devuelve `true` (también en el filtro).
5. `GET /admin/usuarios`: `meta.roles` (cuentas por rol) y órdenes `apellido` y `rol`.
6. `GET /admin/docentes/actividad`: órdenes `-cursos` y `-estudiantes`.
7. `GET /admin/docentes/actividad` devuelve `email` y busca también por correo; la línea de
   tiempo acepta `tipo=contenido` (lecciones, ejercicios y cursos) y `tipo=evaluacion` incluye
   retroalimentaciones.
8. Migración 0035: `editar_cuenta` en `acciones_admin.accion`; `rol_cambiado` y
   `cuenta_suspendida` en `envios_correo.tipo`.

**No incluye**
- Preferencias de avisos y tema en la cuenta (pendiente de confirmar con el equipo).
- Exportar CSV.
- Límite de frecuencia nuevo al reenviar código (ya existe la espera de 1 minuto).
- Pruebas unitarias (decisión del equipo en esta etapa).
