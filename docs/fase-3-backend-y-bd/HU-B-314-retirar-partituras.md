# HU-B-314 · Retirar la tabla `partituras`, que no tiene uso

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD (limpieza) |
| Prioridad | Should |
| Estimación | 1 punto |
| Depende de | HU-B-303 |
| Rama | `hu/HU-B-314-retirar-partituras` |
| Origen | Solicitud del equipo (2026-10-22): eliminar tablas antiguas que ya no son funcionales |

## Historia
**Como** equipo
**quiero** eliminar las tablas que nadie usa
**para** que el esquema refleje solo lo que la plataforma hace.

## Contexto (verificado el 2026-10-22)
| Tabla | Filas | Uso | Decisión |
|---|---|---|---|
| `partituras` | 0 | Ningún endpoint, ni el frontend; ninguna FK la referencia | **Se elimina** (esta HU) |
| `progreso` | 12 | Guarda el resultado de los quizzes por bloque | Se conserva hasta HU-B-308/312 |
| `quiz_preguntas` | 18 | Es el quiz actual | Se conserva hasta HU-B-308 |

## Alcance
**Incluye**
- Revisión `0008` destructiva aprobada: `drop table partituras`, con una **guardia** que aborta si la tabla tiene filas (para no perder datos cargados después de esta verificación).
- `downgrade()` recrea la tabla con su definición original (columnas, CHECK, RLS y política).
- Retirar el modelo `Partitura`.

**No incluye**: `progreso` ni `quiz_preguntas` (siguen en uso).

## Criterios de aceptación
```gherkin
Escenario: Tabla vacia
  Dado que partituras no tiene filas
  Cuando aplico 0008
  Entonces la tabla deja de existir

Escenario: Tabla con datos
  Dado que alguien inserto filas en partituras
  Cuando aplico 0008
  Entonces la migracion aborta sin borrar nada y lo explica

Escenario: Reversible
  Cuando hago downgrade de 0008
  Entonces partituras existe de nuevo con su definicion original
```
