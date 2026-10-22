# HU-B-306 · Preparar el contenido para ser editado (estado, autoría, cascada)

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-305 |
| Rama | `hu/HU-B-306-contenido-editable` |

## Historia
**Como** docente
**quiero** crear lecciones y ejercicios como borrador y publicarlos cuando estén listos
**para** que mis estudiantes no vean contenido incompleto.

## Alcance
**Incluye** — revisión `0005` (esquema) y `0006` (datos):
- `bloques`: `estado`, `actualizado_en`, `unique(orden_index)`.
- `lecciones`: FK `bloque_id` → `bloques.id` **ON DELETE CASCADE** (recrear la FK si hoy es distinta) + índice; `autor_id` (SET NULL); `estado` (`borrador|publicado|archivado`, default `publicado` para no ocultar lo existente); `archivado_en`; `actualizado_en`; `duracion_min int`.
- `ejercicios`: igual, conservando `leccion_id ON DELETE SET NULL`.
- `0006`: convertir `duracion` ("30 min") → `duracion_min` (30) con `regexp_replace`; las columnas `duracion` se eliminan en una revisión posterior marcada destructiva **solo** después de que el frontend use `duracion_min` (HU-B-312).
- Trigger `tocar_actualizado_en` en las tres tablas.
- Repositorios públicos filtran `estado = 'publicado'`.

**No incluye**: endpoints de edición (HU-B-309).

## Prompt de ejecución
```text
Ejecuta HU-B-306 en SIPE-SOUND-BACKEND.
- 0005 esquema, 0006 datos. Ninguna elimina columnas.
- Si la FK lecciones.bloque_id ya existe con otra regla, cambiarla implica
  op.drop_constraint + op.create_foreign_key: marca la línea con
  "# destructivo-aprobado: HU-B-306" (no destruye datos) y pasa -x allow_destructive=true.
- Mantén la respuesta pública con la clave "duracion" (texto) además de
  "duracion_min" hasta HU-B-312.
- Los endpoints públicos solo devuelven contenido publicado.
```

## Criterios de aceptación
```gherkin
Escenario: Contenido existente sigue visible
  Dado las lecciones actuales
  Cuando aplico 0005 y 0006
  Entonces GET /api/v1/lecciones devuelve las mismas lecciones

Escenario: Borrador oculto
  Dado una lección en estado borrador
  Cuando un visitante consulta GET /api/v1/lecciones
  Entonces no aparece

Escenario: Cascada de bloque
  Dado un bloque de prueba con dos lecciones y un ejercicio asociado
  Cuando elimino el bloque en local
  Entonces las lecciones se eliminan y el ejercicio queda con leccion_id nulo
```

## Verificación manual
```bash
uv run alembic upgrade head
uv run python scripts/check_migrations.py
psql "$LOCAL" -c "\d lecciones"   # revisar FK y ON DELETE CASCADE
```

## Definición de hecho específica
- [ ] `duracion_min` poblado para el 100 % de filas cuyo texto contenga un número.
