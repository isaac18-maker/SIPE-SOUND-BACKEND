# HU-B-204 · Unificar errores y respuestas y publicar `/api/v1`

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-203 |
| Rama | `hu/HU-B-204-errores-v1` |

## Historia
**Como** desarrollador del frontend
**quiero** que todas las respuestas y errores tengan la misma forma
**para** manejar errores en un solo lugar y mostrar mensajes claros al estudiante.

## Contexto
- Los errores hoy tienen forma `{ "error": "texto" }` y a veces devuelven `resp.text` crudo de Supabase (fuga de detalles internos).
- Si un recurso no existe, `lecciones/<id>` lanza una excepción de Supabase → 500.

## Alcance
**Incluye**
- `app/core/errors.py` (jerarquía del contrato) y `register_error_handlers(app)`.
- `app/core/responses.py` con `ok()`, `created()`, `no_content()`, `paginated()`.
- Blueprints registrados **dos veces**: en `/api/v1` (con envoltura nueva) y en `/api` (forma antigua) durante la transición.
- Logging básico en `app/core/logging.py`.

**No incluye**: paginación real en repositorios (se agrega cuando un listado la necesite).

## Prompt de ejecución
```text
Ejecuta HU-B-204 en SIPE-SOUND-BACKEND.
- Implementa la jerarquía de errores y los formatos de docs/fase-1-contrato/04-contrato-api.md
  secciones 2 y 3.
- Handlers: AppError -> su status/code; pydantic.ValidationError -> 400 VALIDACION con
  details por campo; werkzeug HTTPException -> forma del contrato; Exception -> 500
  ERROR_INTERNO con log.exception y mensaje genérico.
- Los servicios lanzan AppError; elimina todo `return jsonify({"error": resp.text})`.
- Compatibilidad: crea un "modo legado" para /api/* que devuelve el payload sin
  envolver. Sugerencia: un parámetro `legado` en la fábrica de blueprints o un
  after_request que desenvuelve {"data": ...} solo cuando request.path no empieza
  por /api/v1. Elige la opción más simple y explícala en el PR.
- El frontend actual debe seguir funcionando sin cambios.
```

## Pasos
1. Crear `core/errors.py`, `core/responses.py`, `core/logging.py`.
2. Registrar handlers en `create_app`.
3. Reemplazar retornos de error manuales por excepciones en servicios.
4. Registrar blueprints bajo `/api/v1` y mantener `/api` (legado).
5. Documentar en el README la tabla de transición.

## Criterios de aceptación
```gherkin
Escenario: Recurso inexistente
  Cuando hago GET /api/v1/lecciones/99999
  Entonces recibo 404 con {"error":{"code":"NO_ENCONTRADO", ...}}

Escenario: Validación
  Dado un usuario autenticado
  Cuando hago POST /api/v1/progreso con porcentaje 150
  Entonces recibo 400 con details que mencionan "porcentaje"

Escenario: Sin fugas internas
  Dado que la base de datos devuelve un error
  Cuando el endpoint falla
  Entonces el cliente recibe "ERROR_INTERNO" y el detalle solo queda en el log

Escenario: Compatibilidad
  Cuando hago GET /api/lecciones
  Entonces recibo la lista sin envoltura, igual que antes de esta HU
```

## Verificación manual
```bash
curl -s localhost:5000/api/v1/lecciones | head -c 120     # {"data":[...
curl -s localhost:5000/api/lecciones | head -c 120        # [...
curl -s -i localhost:5000/api/v1/lecciones/99999          # 404 + code
curl -s -i localhost:5000/api/v1/no-existe                # 404 con forma del contrato
```

## Definición de hecho específica
- [ ] `grep -rn "resp.text" app/` sin resultados.
- [ ] El frontend actual (sin cambios) carga Home, Acordes, Ejercicios y Progreso.
