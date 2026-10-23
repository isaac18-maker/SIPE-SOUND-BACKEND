# HU-B-317 · Estandarizar la respuesta de la API y validar Swagger

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-204, HU-B-307 |
| Rama | `hu/HU-B-317-respuesta-estandar` |
| Origen | Solicitud del equipo (2026-10-23) |

## Historia
**Como** desarrollador del frontend
**quiero** que todos los endpoints respondan con la misma estructura, también en los errores
**para** procesar cualquier respuesta con una sola función y mostrar mensajes claros.

## Alcance
- Estructura única en `/api/v1`: `statusCode`, `status`, `data`, `success`, `message`, `errors`, `timestamp`, `meta`.
- `/api` (legado) conservaba su forma; se retiró en HU-B-319.
- Swagger: solo `/api/v1`, esquema `RespuestaEstandar` en todas las operaciones y desactivado en producción.

## Criterios de aceptación
```gherkin
Escenario: Exito y error con la misma forma
  Cuando consulto un recurso existente y uno inexistente en /api/v1
  Entonces ambas respuestas tienen las 8 claves, con success true y false

Escenario: Swagger sin duplicados
  Cuando abro /openapi.json
  Entonces no aparece ninguna ruta fuera de /api/v1

Escenario: Swagger en produccion
  Dado APP_ENV=production
  Cuando abro /docs
  Entonces recibo 404
```
