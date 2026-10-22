# HU-B-206 · Inventariar el esquema real de la base de datos

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 2 puntos |
| Depende de | HU-B-201 |
| Rama | `hu/HU-B-206-inventario-esquema` |

## Historia
**Como** responsable de la base de datos
**quiero** un inventario fiel del esquema que existe hoy en Supabase
**para** construir la migración *baseline* de Alembic sin perder tablas, políticas ni triggers.

## Contexto
El único script disponible es `database/schema.sql` del antiguo monorepo (`SIPE-SOUND-FULLSTACK`) y está **desactualizado** respecto al código:

| El código usa | ¿Está en schema.sql? |
|---|---|
| Tabla `bloques` (`numero`, `titulo`, `descripcion`, `orden_index`) | ❌ |
| `lecciones.bloque_id` | ❌ |
| Tabla `quiz_preguntas` (`bloque_id`, `pregunta`, `opciones`, `respuesta_correcta`, `orden_index`) | ❌ |
| `progreso.tipo = 'bloque'` | ❌ (CHECK solo permite `leccion`, `ejercicio`) |
| `acordes.diagram` (lo usa `ChordDiagram`) | ❌ |
| `partituras` | ✅ pero ningún endpoint la usa |

## Alcance
**Incluye**
- Copiar el script histórico a `db/legacy/schema_supabase_v0.sql` (solo referencia, con cabecera "NO EJECUTAR").
- Extraer el esquema **real** de `public` con `pg_dump --schema-only --schema=public` a `db/legacy/schema_real_YYYYMMDD.sql`.
- Documento `db/legacy/INVENTARIO.md`: tablas, columnas, FK y su `ON DELETE`, índices, CHECK, políticas RLS, funciones y triggers (`handle_new_user`, `on_auth_user_created`).

**No incluye**: modificar la base de datos.

## Prompt de ejecución
```text
Ejecuta HU-B-206 en SIPE-SOUND-BACKEND. Solo lectura sobre la base de datos.
1) Copia ../SIPE-SOUND-FULLSTACK/database/schema.sql a db/legacy/schema_supabase_v0.sql
   y antepón un comentario: "-- HISTORICO. NO EJECUTAR. Ver migrations/".
2) Pide al usuario que ejecute (tú no tienes la contraseña):
   pg_dump "<cadena de conexion DIRECTA de Supabase, puerto 5432>" --schema-only --schema=public --no-owner --no-privileges > db/legacy/schema_real_<fecha>.sql
   y, para las políticas: select * from pg_policies where schemaname='public';
3) Con esos archivos redacta db/legacy/INVENTARIO.md con las secciones de la HU
   y una tabla "Diferencias código vs. BD".
No ejecutes ninguna sentencia que modifique datos o estructura.
```

## Criterios de aceptación
```gherkin
Escenario: Inventario completo
  Dado el dump real de public
  Cuando reviso db/legacy/INVENTARIO.md
  Entonces cada tabla del dump aparece con sus FK, su ON DELETE y sus políticas RLS

Escenario: Diferencias identificadas
  Entonces el inventario lista cada tabla o columna usada por el código que no exista en la BD (o viceversa)
```

## Verificación manual
```bash
grep -c "CREATE TABLE" db/legacy/schema_real_*.sql
grep -c "^### " db/legacy/INVENTARIO.md     # debe coincidir con el número de tablas
```

## Definición de hecho específica
- [ ] El dump no contiene datos (`--schema-only`) ni credenciales.
- [ ] El equipo del frontend sabe que `database/` saldrá de su repo (HU-F-206).
