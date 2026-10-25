# HU-B-411 · Términos y condiciones editables y aceptación por versión

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-405, HU-B-323 |
| Rama | `hu/HU-B-411-terminos-editables` |
| Relacionada | HU-F-510 |

## Historia
**Como** administrador
**quiero** editar los términos y condiciones y, si el cambio es una versión nueva, exigir que todos los lean y los acepten
**para** mantener el consentimiento vigente (Ley 1581 de 2012) sin tocar el código.

## Alcance
**Incluye**
1. Tabla `documentos_legales` (migración 0026): texto en Markdown, `version`, `actualizado_por`
   (SET NULL) y `actualizado_en`. Se siembra con el texto que estaba en el frontend (versión 1).
2. `profiles.terminos_version` y `terminos_aceptados_en`. Las cuentas existentes quedan en la
   versión 1; las nuevas la reciben al verificar su correo (el registro ya exige la casilla).
3. `GET /terminos` (público), `GET` y `PUT /admin/terminos`, `POST /me/terminos` (contrato 04).
4. **Bloqueo**: con una versión pendiente, toda ruta con `roles_required` responde 403 hasta que la
   cuenta acepte. `GET /me` indica `terminos_pendientes` para que el frontend muestre el aviso.
5. `PUT` con `nueva_version: true` sube el número (todos deben aceptar); `false` corrige sin pedir nada.

**No incluye**
- Historial de versiones anteriores ni evidencia de cada aceptación pasada (solo la última).
- Auditoría en `acciones_admin` (guarda quién y cuándo en el propio documento).

## Criterios de aceptación (Gherkin)
```gherkin
Escenario: Versión nueva
  Dado que el administrador guarda los términos con nueva_version true
  Cuando una cuenta con la versión anterior llama a una ruta protegida
  Entonces recibe 403 "Lee y acepta los términos y condiciones actualizados para continuar."

Escenario: Aceptar
  Cuando esa cuenta envía POST /me/terminos con la versión vigente
  Entonces recibe 200 y vuelve a usar la API

Escenario: Corrección menor
  Cuando el administrador guarda con nueva_version false
  Entonces nadie tiene que volver a aceptar

Escenario: Versión desactualizada
  Cuando se envía una versión que ya no es la vigente
  Entonces recibe 409
```

## Verificación manual
```bash
uv run alembic upgrade head
curl -s localhost:8000/api/v1/terminos
```

## Definición de hecho específica
- [ ] Migración revisada y aplicada; la guardia de migraciones pasa.
- [ ] Ninguna ruta de `roles_required` responde 200 a una cuenta con términos pendientes.
