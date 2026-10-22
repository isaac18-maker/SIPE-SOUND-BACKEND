# HU-B-305 · Rediseñar el progreso con claves foráneas y borrado en cascada

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-304 |
| Rama | `hu/HU-B-305-progreso` |

## Historia
**Como** docente
**quiero** que el progreso de mis estudiantes sea confiable y desaparezca solo cuando corresponde
**para** no ver registros huérfanos de lecciones eliminadas ni perder avances por error.

## Contexto
`progreso` es polimórfica (`tipo` + `contenido_id`): no admite FK, por lo que si se borra una lección su progreso queda huérfano y la cascada es imposible. Además mezcla progreso de bloque (resultado de quiz) con lecciones y ejercicios.

## Alcance
**Incluye**
- Revisión `0003` (esquema): crear `progreso_lecciones` y `progreso_ejercicios` según [modelo objetivo](00-modelo-de-datos-objetivo.md), con FK **CASCADE**, PK compuesta, CHECK e índices; RLS habilitado con políticas "propio progreso".
- Revisión `0004` (datos): copiar filas de `progreso` con `tipo in ('leccion','ejercicio')` cuyo `contenido_id` exista; reportar con `RAISE NOTICE` cuántas filas huérfanas se descartan. Idempotente (`ON CONFLICT DO NOTHING`).
- Repositorio y servicio de progreso sobre SQLAlchemy.
- Endpoints nuevos: `PUT /api/v1/progreso/lecciones/{id}`, `PUT /api/v1/progreso/ejercicios/{id}`, `GET /api/v1/progreso/resumen`.
- `GET/POST /api/v1/progreso` (antiguos) siguen funcionando leyendo/escribiendo en las tablas nuevas (adaptador).

**No incluye**
- Las filas `tipo='bloque'` (se migran en HU-B-308 hacia `intentos_evaluacion`).
- Eliminar la tabla `progreso` (se hace en HU-B-312, con marca destructiva).

## Prompt de ejecución
```text
Ejecuta HU-B-305 en SIPE-SOUND-BACKEND.
- Crea 0003 (esquema) y 0004 (datos) como revisiones separadas.
- 0004 debe ser idempotente y no borrar nada de la tabla progreso.
- El upsert usa INSERT ... ON CONFLICT (estudiante_id, leccion_id) DO UPDATE y
  nunca baja "completado" de true a false.
- Mantén compatibilidad de GET/POST /api/v1/progreso con un adaptador en el servicio.
- Verifica la cascada en local: borrar una lección de prueba elimina su progreso.
```

## Criterios de aceptación
```gherkin
Escenario: Migración de datos sin pérdida
  Dado N filas válidas de tipo leccion o ejercicio en progreso
  Cuando aplico 0004
  Entonces progreso_lecciones + progreso_ejercicios contienen N filas
  Y la salida informa cuántas filas huérfanas se ignoraron

Escenario: Cascada
  Dado una lección sin uso real con progreso de un estudiante de prueba
  Cuando la elimino directamente en la base local
  Entonces su fila en progreso_lecciones desaparece

Escenario: Completado no retrocede
  Dado una lección marcada completada
  Cuando envío PUT con completado=false y porcentaje=40
  Entonces completado sigue en true y porcentaje queda en el máximo registrado
```

## Verificación manual
```bash
uv run alembic upgrade head
psql "$LOCAL" -c "select count(*) from progreso where tipo in ('leccion','ejercicio');"
psql "$LOCAL" -c "select (select count(*) from progreso_lecciones)+(select count(*) from progreso_ejercicios);"
uv run alembic downgrade -2 && uv run alembic upgrade head
```

## Definición de hecho específica
- [ ] Ambas revisiones con cabecera completa (HU, Tipo).
- [ ] HU-F correspondiente notificada del nuevo endpoint `PUT`.
