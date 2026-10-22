# HU-B-205 · Consolidar la autenticación en un módulo de seguridad

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-204 |
| Rama | `hu/HU-B-205-seguridad` |

## Historia
**Como** desarrollador
**quiero** obtener el usuario autenticado desde un único objeto tipado
**para** aplicar reglas de rol en la Fase 3 sin repetir lógica en cada ruta.

## Contexto
- `auth_required` guarda `g.user_id` y `g.token` sueltos.
- Cada petición autenticada hace una llamada HTTP a Supabase (`auth.get_user`) → latencia y dependencia de red.
- `token = auth_header.split(" ")[1]` no valida el formato.

## Alcance
**Incluye**
- `app/core/security.py`: `CurrentUser` (dataclass: `id`, `email`, `token`), `auth_required`, `get_current_user()`.
- Verificación **local** del JWT con PyJWT:
  - Si existe `SUPABASE_JWKS_URL` → algoritmo asimétrico (`ES256`/`RS256`) con `PyJWKClient` (cacheado).
  - Si no, `SUPABASE_JWT_SECRET` → `HS256` (proyectos con clave legada).
  - Validar `exp`, `aud = "authenticated"`, `iss = {SUPABASE_URL}/auth/v1`.
- Esqueleto de `roles_required(*roles)` que por ahora **solo** exige autenticación (los roles llegan en HU-B-304).

**No incluye**: tabla de roles ni autorización por recurso.

## Prompt de ejecución
```text
Ejecuta HU-B-205 en SIPE-SOUND-BACKEND.
- uv add "pyjwt[crypto]".
- Implementa app/core/security.py como describe la HU. Lanza NoAutenticado
  (core/errors) en vez de devolver jsonify.
- Reemplaza g.user_id/g.token por get_current_user() en servicios/controladores.
- Agrega SUPABASE_JWT_SECRET y SUPABASE_JWKS_URL a Settings y a .env.example
  (al menos una obligatoria).
- No registres tokens en logs. No cambies las rutas ni las respuestas.
```

## Pasos
1. Dependencia y variables nuevas.
2. `CurrentUser` y verificación local con caché de JWKS.
3. Reemplazar usos de `g.*`.
4. Eliminar `app/auth.py`.

## Criterios de aceptación
```gherkin
Escenario: Token válido
  Dado un access_token vigente de Supabase
  Cuando llamo GET /api/v1/progreso
  Entonces recibo 200 y no se hace ninguna llamada HTTP a /auth/v1/user

Escenario: Token expirado
  Cuando llamo con un token expirado
  Entonces recibo 401 NO_AUTENTICADO

Escenario: Cabecera mal formada
  Cuando envío "Authorization: Bearer"
  Entonces recibo 401 y no un 500
```

## Verificación manual
```bash
TOKEN=<copiar desde el navegador: supabase.auth.getSession()>
curl -s -H "Authorization: Bearer $TOKEN" localhost:5000/api/v1/progreso
curl -s -i -H "Authorization: Bearer" localhost:5000/api/v1/progreso
curl -s -i -H "Authorization: Bearer abc.def.ghi" localhost:5000/api/v1/progreso
```

## Definición de hecho específica
- [ ] `app/auth.py` eliminado.
- [ ] `grep -rn "g.user_id\|g.token" app/` sin resultados.
