# HU-B-320 · Límites de los campos en la API y en la base

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-319 |
| Rama | `hu/HU-B-320-limites-de-campos` |
| Origen | Solicitud del equipo (2026-10-24) |

## Historia
**Como** equipo
**quiero** que cada dato que escriben las personas tenga el mismo límite en el formulario, en la API y en la base
**para** que ningún camino (frontend, API, cliente de Supabase o SQL directo) guarde datos inválidos o desmedidos.

## Alcance
1. `app/core/longitudes.py`: fuente única de límites para los esquemas Pydantic.
2. Registro e invitación: nombre de persona solo con letras, espacios, `'`, `.` y `-`.
3. Unirse a curso: el código se valida contra el alfabeto (sin `0 O 1 I L`).
4. Revisión `0013`: CHECK de longitud, rango, patrón y número de elementos en
   `profiles`, `bloques`, `lecciones`, `ejercicios`, `acordes` y `cursos`
   (tabla completa en [04-contrato-api §7](../fase-1-contrato/04-contrato-api.md#7-límites-de-los-campos-hu-b-320)).
5. `handle_new_user()` normaliza el nombre (espacios, máximo 80, respaldo con la
   parte local del correo o `Usuario`) y fija `search_path = ''`.
6. Una `SUPABASE_SERVICE_ROLE_KEY` vacía cuenta como no configurada (503 sin llamar a Supabase).

## Criterios de aceptación
```gherkin
Escenario: La base rechaza aunque se salte la API
  Cuando ejecuto "update lecciones set titulo = repeat('a', 121)"
  Entonces PostgreSQL responde violación de ck_lecciones_titulo

Escenario: La API rechaza con el mismo límite
  Cuando registro un estudiante con nombre "ana123"
  Entonces recibo 400 con errors ["nombre: Usa solo letras, espacios, apóstrofo, punto o guion."]

Escenario: Registro sin nombre
  Cuando Supabase crea un usuario sin nombre en sus metadatos
  Entonces el perfil toma la parte local del correo y no falla
```

## Despliegue
Después de `0012` (HU-B-319): respaldo, `uv run alembic upgrade head`, `uv run alembic check`.
En Supabase → Authentication → Providers → Email: longitud mínima de contraseña 8 y
"letras y dígitos", para que el límite también aplique a quien use Supabase directamente.
