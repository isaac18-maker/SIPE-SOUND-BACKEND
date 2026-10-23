# Inventario del esquema de base de datos (HU-B-206)

> Fuente de verdad para la migración *baseline* (HU-B-303) y los modelos (HU-B-301).
> Generado el 2026-10-21 contra PostgreSQL **17.6** (Supabase) con
> `scripts/inventariar_esquema.py` en **modo solo lectura**.
> Detalle completo en [`schema_real_20261021.sql`](schema_real_20261021.sql).
> `schema_supabase_v0.sql` es **histórico** y está desactualizado.

## Resumen

| Tabla | Filas (visibles a `anon`) | PK | FK salientes | RLS | Usada por el backend |
|---|---|---|---|---|---|
| `acordes` | 14 | `id serial` | — | ✅ | `GET /acordes` |
| `bloques` | 6 | `id serial` | — | ✅ | `GET /bloques` |
| `ejercicios` | 3 | `id serial` | `leccion_id → lecciones` SET NULL | ✅ | `GET /ejercicios`, `POST /progreso` |
| `lecciones` | 8 | `id serial` | `bloque_id → bloques` SET NULL | ✅ | `GET /lecciones`, `POST /progreso` |
| `partituras` | 0 | `id serial` | — | ✅ | ❌ Sin uso |
| `profiles` | (solo el dueño) | `id uuid` | `id → auth.users` CASCADE | ✅ | ❌ Sin uso directo (lo crea un trigger) |
| `progreso` | (solo el dueño) | `id uuid` | `usuario_id → auth.users` CASCADE | ✅ | `GET/POST /progreso`, quiz |
| `quiz_preguntas` | 18 | `id serial` | `bloque_id → bloques` CASCADE | ✅ | `GET /quiz`, verificación |

### acordes
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('acordes_id_seq')` |
| `nombre` | text | no | — |
| `tipo` | text | sí | — |
| `descripcion` | text | sí | — |
| `dificultad` | text | sí | `'facil'` |
| `creado_en` | timestamptz | sí | `now()` |
| `diagram` | jsonb | sí | — |

Restricciones: `acordes_nombre_key UNIQUE (nombre)`, `acordes_dificultad_check` (`facil`, `medio`, `dificil`), `acordes_tipo_check` (`mayor`, `menor`, `septima`, `disminuido`).

### bloques
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('bloques_id_seq')` |
| `numero` | integer | no | — |
| `titulo` | text | no | — |
| `descripcion` | text | sí | — |
| `nivel` | text | no | `'principiante'` |
| `orden_index` | integer | no | — |
| `creado_en` | timestamptz | sí | `now()` |

Restricciones: `bloques_nivel_check` (`principiante`, `intermedio`, `avanzado`). **Sin `UNIQUE (orden_index)`.**

### ejercicios
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('ejercicios_id_seq')` |
| `leccion_id` | integer | sí | — |
| `nombre` | text | no | — |
| `descripcion` | text | sí | — |
| `nivel` | text | no | `'principiante'` |
| `bpm_recomendado` | integer | sí | `60` |
| `duracion` | text | sí | — |
| `compas` | text | sí | `'4/4'` |
| `acordes` | text[] | sí | — |
| `pasos` | text[] | sí | — |
| `creado_en` | timestamptz | sí | `now()` |

Restricciones: `ejercicios_leccion_id_fkey → lecciones(id) ON DELETE SET NULL`, `ejercicios_nivel_check`.

### lecciones
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('lecciones_id_seq')` |
| `numero` | integer | no | — |
| `titulo` | text | no | — |
| `descripcion` | text | sí | — |
| `nivel` | text | no | `'principiante'` |
| `duracion` | text | sí | — |
| `acordes` | text[] | sí | — |
| `temas` | text[] | sí | — |
| `creado_en` | timestamptz | sí | `now()` |
| `contenido` | text | sí | — |
| `bloque_id` | integer | **sí** | — |

Restricciones: `lecciones_bloque_id_fkey → bloques(id) ON DELETE SET NULL`, `lecciones_nivel_check`.

### partituras
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('partituras_id_seq')` |
| `titulo` | text | no | — |
| `artista` | text | sí | — |
| `nivel` | text | sí | `'principiante'` |
| `tipo` | text | sí | — |
| `acordes` | text[] | sí | — |
| `imagen_url` | text | sí | — |
| `creado_en` | timestamptz | sí | `now()` |

Restricciones: `partituras_nivel_check`, `partituras_tipo_check` (`partitura`, `tablatura`, `ambas`).

### profiles
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | uuid | no | — |
| `nombre` | text | no | — |
| `nivel` | text | no | `'principiante'` |
| `creado_en` | timestamptz | sí | `now()` |

Restricciones: `profiles_id_fkey → auth.users(id) ON DELETE CASCADE`, `profiles_nivel_check`.

### progreso
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | uuid | no | `gen_random_uuid()` |
| `usuario_id` | uuid | no | — |
| `tipo` | text | no | — |
| `contenido_id` | integer | no | — |
| `porcentaje` | integer | no | `0` |
| `completado` | boolean | sí | `false` |
| `actualizado_en` | timestamptz | sí | `now()` |

Restricciones: `progreso_usuario_id_tipo_contenido_id_key UNIQUE (usuario_id, tipo, contenido_id)`, `progreso_usuario_id_fkey → auth.users(id) ON DELETE CASCADE`, `progreso_porcentaje_check` (0–100), `progreso_tipo_check` (`leccion`, `ejercicio`, **`bloque`**).

### quiz_preguntas
| Columna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | integer | no | `nextval('quiz_preguntas_id_seq')` |
| `bloque_id` | integer | no | — |
| `pregunta` | text | no | — |
| `opciones` | **text[]** | no | — |
| `respuesta_correcta` | integer | no | — |
| `orden_index` | integer | no | — |
| `creado_en` | timestamptz | sí | `now()` |

Restricciones: `quiz_preguntas_bloque_id_fkey → bloques(id) ON DELETE CASCADE`. Sin CHECK de rango para `respuesta_correcta`.

## Índices

Solo existen los de PK y UNIQUE. **Ninguna columna FK tiene índice**
(`lecciones.bloque_id`, `ejercicios.leccion_id`, `quiz_preguntas.bloque_id`,
`progreso.usuario_id` queda cubierta por el UNIQUE compuesto).

## RLS, políticas y privilegios

RLS habilitado en las 8 tablas.

| Tabla | Políticas |
|---|---|
| `acordes`, `bloques`, `ejercicios`, `lecciones`, `partituras`, `quiz_preguntas` | `SELECT` para `public` con `using (true)` |
| `profiles` | `SELECT` y `UPDATE` con `auth.uid() = id` (sin `INSERT`: lo hace el trigger con `SECURITY DEFINER`) |
| `progreso` | `SELECT`, `INSERT` y `UPDATE` con `auth.uid() = usuario_id` (sin `DELETE`) |

Privilegios de tabla para `anon` y `authenticated` en **todas** las tablas:
`SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER` (grants por defecto de Supabase; RLS es lo que realmente limita).

## Funciones y triggers

| Objeto | Tipo | Dueño lógico | Para la baseline |
|---|---|---|---|
| `public.handle_new_user()` | función `SECURITY DEFINER` | **Proyecto** | ✅ Incluir (`op.execute`) |
| `on_auth_user_created` en `auth.users` | trigger `AFTER INSERT` | **Proyecto** | ✅ Incluir (`op.execute`) |
| `public.rls_auto_enable()` | función de event trigger | Supabase | ❌ **Excluir**: la gestiona Supabase |
| `ensure_rls` | event trigger `ddl_command_end` (`CREATE TABLE`) | Supabase | ❌ Excluir. **Efecto:** toda tabla nueva en `public` nace con RLS activo y sin políticas |
| `issue_*`, `pgrst_*` | event triggers | Supabase | ❌ Excluir |

## Diferencias código ↔ base de datos

| Elemento | Código | Base real | Impacto |
|---|---|---|---|
| `progreso.tipo = 'bloque'` | `QuizService` lo escribe | ✅ Permitido por el CHECK | Ninguno. El script histórico estaba desactualizado. |
| `lecciones.contenido` | Ni backend ni frontend lo usan | Existe (`text`, nullable) | Conservar en la baseline; decidir su uso en HU-B-306. |
| `acordes.diagram` | El frontend lo usa (`ChordDiagram`) | Existe (`jsonb`) | Ninguno. |
| `lecciones.bloque_id` | Se asume obligatorio (ruta por bloques) | Nullable, `ON DELETE SET NULL` | HU-B-306 lo pasa a CASCADE según el contrato. Antes, verificar que no haya lecciones con `bloque_id` nulo. |
| `quiz_preguntas.opciones` | Se trata como lista | `text[]` | HU-B-308: `preguntas_evaluacion.opciones` será `jsonb`; la migración de datos debe convertir con `to_jsonb(opciones)`. |
| `partituras` | Sin uso | 0 filas visibles | Se conserva (decisión de producto pendiente). |

## 🔴 Hallazgo crítico de seguridad: respuestas de los quizzes públicas

**Confirmado:** la política `Lectura publica quiz_preguntas` es `SELECT using (true)` y
`anon` tiene `SELECT` sobre la tabla completa, columna `respuesta_correcta` incluida.
Con la *anon key* (pública, viaja en el frontend) cualquiera obtiene las 18 respuestas:

```
GET https://<proyecto>.supabase.co/rest/v1/quiz_preguntas?select=id,respuesta_correcta
```

(Verificado el 2026-10-21 sin registrar valores.)

**Por qué no se corrige en esta HU:** el backend lee `respuesta_correcta` con la *anon key*
para calificar (`SupabaseQuizRepository.preguntas_con_respuesta`); retirar el permiso
rompería los quizzes. Además, el contrato exige hacer el cambio con una migración.

**Corrección planificada:**
1. HU-B-301: el backend lee con su propia conexión (SQLAlchemy), sin la *anon key*.
2. Primera revisión tras la baseline:
   ```sql
   revoke select on public.quiz_preguntas from anon, authenticated;
   grant select (id, bloque_id, pregunta, opciones, orden_index, creado_en)
     on public.quiz_preguntas to anon, authenticated;
   ```
3. HU-B-308: `preguntas_evaluacion` sin políticas para `anon`/`authenticated`.

## Otros hallazgos

| Severidad | Hallazgo | HU que lo resuelve |
|---|---|---|
| Media | Columnas FK sin índice | HU-B-306/307 (índice en toda FK, contrato de BD §4) |
| Media | `lecciones.bloque_id` nullable con SET NULL: una lección puede quedar fuera de la ruta sin aviso | HU-B-306 |
| Baja | `anon`/`authenticated` tienen `TRUNCATE`, que RLS no controla. No es explotable por la API de Supabase (PostgREST no expone `TRUNCATE`), pero conviene revocarlo como defensa en profundidad | Revisión de seguridad tras la baseline |
| Baja | `bloques.orden_index` sin `UNIQUE`: dos bloques pueden empatar en orden | HU-B-306 |
| Baja | `quiz_preguntas.respuesta_correcta` sin CHECK contra el número de opciones | HU-B-308 |
| Info | `ensure_rls` activa RLS en toda tabla nueva: las tablas de la Fase 3 nacen cerradas | Tenerlo en cuenta en HU-B-303 y siguientes |
