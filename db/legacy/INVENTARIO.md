# Inventario del esquema de base de datos (HU-B-206)

> **Estado: PRELIMINAR.** Las secciones marcadas ⏳ se completan al ejecutar
> `scripts/inventariar_esquema.py` contra la conexión directa de Supabase
> (requiere `DATABASE_URL_MIGRATIONS`). Hasta entonces, este documento **no**
> sirve como base para la migración *baseline* (HU-B-303).

## Fuentes

| Fuente | Qué aporta | Fiabilidad |
|---|---|---|
| `schema_supabase_v0.sql` | Script histórico del monorepo | ❌ Desactualizado |
| Lectura con la *anon key* (2026-10-21) | Tablas y columnas **legibles públicamente**, número de filas visibles | ✅ Real, pero parcial (solo lo que RLS deja ver a un visitante) |
| `schema_real_<fecha>.sql` | Tipos, nulabilidad, defaults, CHECK, FK con ON DELETE, índices, RLS, políticas, privilegios, funciones y triggers | ⏳ Pendiente |

## Tablas encontradas

Lectura pública con la *anon key* el 2026-10-21:

| Tabla | Filas visibles (anon) | Columnas | ¿En `schema_supabase_v0.sql`? |
|---|---|---|---|
| `bloques` | 6 | `id`, `numero`, `titulo`, `descripcion`, `nivel`, `orden_index`, `creado_en` | ❌ No existe |
| `lecciones` | 8 | `id`, `numero`, `titulo`, `descripcion`, `contenido`, `nivel`, `duracion`, `acordes`, `temas`, `bloque_id`, `creado_en` | ⚠️ Faltan `bloque_id` y `contenido` |
| `ejercicios` | 3 | `id`, `leccion_id`, `nombre`, `descripcion`, `nivel`, `bpm_recomendado`, `duracion`, `compas`, `acordes`, `pasos`, `creado_en` | ✅ Coincide |
| `acordes` | 14 | `id`, `nombre`, `tipo`, `descripcion`, `dificultad`, `diagram`, `creado_en` | ⚠️ Falta `diagram` |
| `quiz_preguntas` | 18 | `id`, `bloque_id`, `pregunta`, `opciones`, `respuesta_correcta`, `orden_index`, `creado_en` | ❌ No existe |
| `progreso` | 0 (RLS: solo el dueño) | ⏳ | ⚠️ El código usa `tipo = 'bloque'`; el CHECK del script solo permite `leccion` y `ejercicio` |
| `profiles` | 0 (RLS: solo el dueño) | ⏳ | ✅ Según el script |
| `partituras` | 0 visibles | ⏳ | ✅ Pero ningún endpoint la usa. ⏳ Confirmar si tiene filas o si su política de lectura pública ya no existe |

## Diferencias código ↔ base de datos

| Elemento | Código | Base de datos | Acción |
|---|---|---|---|
| `lecciones.contenido` | No se usa en el backend | Existe | ⏳ Confirmar tipo; incluir en la baseline. Revisar si el frontend lo usa (`LeccionDetalle`). |
| `progreso.tipo = 'bloque'` | `QuizService` lo escribe | ⏳ ¿El CHECK lo permite? | Si el CHECK no lo permite, el guardado de quizzes estaría fallando en producción. |
| `partituras` | Sin uso | Existe | Se conserva (decisión de producto pendiente, ver modelo objetivo). |

## 🔴 Hallazgo crítico de seguridad

**Las respuestas correctas de todos los quizzes son públicas.** Con la *anon key*
(que viaja en el frontend) cualquiera puede ejecutar:

```
GET https://<proyecto>.supabase.co/rest/v1/quiz_preguntas?select=id,respuesta_correcta
```

y obtener las 18 respuestas (verificado el 2026-10-21; no se registraron valores).
El backend las oculta en `GET /quiz/{id}`, pero la política RLS de la tabla permite
leer **todas** las columnas, así que la protección del backend se puede saltar.

**Por qué no se corrige ya:** el propio backend lee `respuesta_correcta` con la
*anon key* para calificar (`SupabaseQuizRepository.preguntas_con_respuesta`).
Quitar el permiso hoy rompería la calificación.

**Corrección propuesta** (respeta el contrato: todo cambio de esquema por migración):
1. HU-B-301: el backend lee con su propia conexión de servidor (SQLAlchemy), sin depender de la *anon key*.
2. Primera migración después de la baseline (HU-B-303/304):
   ```sql
   revoke select on public.quiz_preguntas from anon, authenticated;
   grant select (id, bloque_id, pregunta, opciones, orden_index, creado_en)
     on public.quiz_preguntas to anon, authenticated;
   ```
3. HU-B-308 lo resuelve de forma definitiva: `preguntas_evaluacion` sin políticas para `anon`/`authenticated`.

Mientras tanto, el riesgo es que un estudiante apruebe bloques sin dominar el contenido.
No hay exposición de datos personales.

## ⏳ Pendiente de `schema_real_<fecha>.sql`

Por cada tabla:
- Tipos exactos, nulabilidad y defaults.
- CHECK (en especial `progreso.tipo`, `nivel`, `dificultad`).
- FK y su regla `ON DELETE`. Hoy solo se sabe por el script: `profiles → auth.users` CASCADE, `ejercicios.leccion_id` SET NULL y `progreso.usuario_id` CASCADE. `lecciones.bloque_id` y `quiz_preguntas.bloque_id` no se conocen.
- Índices.
- RLS habilitado, políticas y privilegios de `anon`/`authenticated`.

Objetos globales:
- Funciones de `public` (se espera `handle_new_user`).
- Triggers (se espera `on_auth_user_created` en `auth.users`).
