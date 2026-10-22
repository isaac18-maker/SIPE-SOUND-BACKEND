# HU-B-203 · Reestructurar en capas y reubicar el código existente

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-202 |
| Rama | `hu/HU-B-203-capas` |

## Historia
**Como** desarrollador que va a construir el panel docente
**quiero** que cada endpoint esté separado en controlador, servicio y repositorio
**para** poder cambiar la fuente de datos (Supabase → SQLAlchemy) y agregar reglas de negocio sin reescribir rutas.

## Contexto
Hoy cada archivo de [app/routes/](../../app/routes/) mezcla HTTP, validación, reglas de negocio y acceso a datos. El caso más evidente es [app/routes/quiz.py](../../app/routes/quiz.py): califica, compara con el mejor intento previo y hace upsert, todo en una función de ~80 líneas.

## Mapa de reubicación

| Origen | Destino | Qué se lleva |
|---|---|---|
| `app/routes/health.py` | `app/api/v1/health.py` | Igual. |
| `app/routes/bloques.py` | `app/api/v1/bloques.py` + `app/services/bloque_service.py` + `app/repositories/supabase/bloque_repository.py` | Consulta ordenada por `orden_index` → repositorio. |
| `app/routes/lecciones.py` | `api/v1/lecciones.py` + `services/leccion_service.py` + `repositories/supabase/leccion_repository.py` | `NoEncontrado` si `obtener()` devuelve `None`. |
| `app/routes/ejercicios.py` | `api/v1/ejercicios.py` + `services/ejercicio_service.py` + `repositories/supabase/ejercicio_repository.py` | |
| `app/routes/acordes.py` | `api/v1/acordes.py` + `services/acorde_service.py` + `repositories/supabase/acorde_repository.py` | |
| `app/routes/progreso.py` | `api/v1/progreso.py` + `services/progreso_service.py` + `repositories/supabase/progreso_repository.py` + `schemas/progreso.py` | Validaciones manuales → `ProgresoCreate` (Pydantic). Verificación de existencia del contenido → servicio. |
| `app/routes/quiz.py` | `api/v1/quiz.py` + `services/quiz_service.py` + `repositories/supabase/quiz_repository.py` + `schemas/quiz.py` | Cálculo de puntaje → función pura `calificar(preguntas, respuestas)`. Regla "no rebajar mejor nota" → `QuizService`. `PORCENTAJE_APROBACION` → `core/constants.py`. |
| `app/auth.py` → `supabase_rest()` | `app/infrastructure/supabase_rest.py` | Igual (se retira en Fase 3). |
| `app/auth.py` → `auth_required` | `app/core/security.py` | Ver HU-B-205. En esta HU solo se mueve. |
| `app/extensions.py` | **eliminado** | Shim de HU-B-202 ya no es necesario. |
| `app/routes/` | **eliminado** | |
| — | `app/repositories/base.py` | Protocolos `LectorBloques`, `LectorLecciones`, … |
| — | `app/core/container.py` | Fábricas que ensamblan servicio + repositorio. |

## Alcance
**Incluye**: todo el mapa anterior. Los endpoints conservan **ruta y forma de respuesta** (`/api/...`).
**No incluye**: envoltura `{data}` ni `/api/v1` (HU-B-204), cambios de autenticación (HU-B-205).

## Prompt de ejecución
```text
Ejecuta HU-B-203 en SIPE-SOUND-BACKEND siguiendo el "Mapa de reubicación"
de la HU al pie de la letra. Reglas:
- Usa `git mv` cuando un archivo se mueve completo para conservar historial.
- Los controladores solo: leen request, validan con schema, llaman al servicio,
  devuelven jsonify (la envoltura llega en HU-B-204).
- Los servicios reciben repositorios por constructor (tipados con Protocol).
- Los repositorios en app/repositories/supabase/ usan get_supabase() o
  supabase_rest(); NO contienen reglas de negocio.
- La calificación del quiz es una función pura sin I/O en services/quiz_service.py.
- Las rutas y las respuestas JSON deben ser idénticas a las actuales. Antes de
  empezar, guarda la salida de cada GET en /tmp o en el scratchpad y compárala al final.
- No escribas pruebas unitarias.
```

## Pasos
1. Capturar salida actual de todos los GET (línea base).
2. Crear paquetes vacíos: `app/api/v1`, `app/services`, `app/repositories/supabase`, `app/schemas`.
3. Definir protocolos en `repositories/base.py`.
4. Migrar endpoint por endpoint, en el orden: health → acordes → ejercicios → bloques → lecciones → progreso → quiz. **Un commit por endpoint.**
5. Crear `api/v1/__init__.py` con `register_blueprints(app)`; `create_app` solo llama a esa función.
6. Eliminar `app/routes/` y `app/extensions.py`.
7. Comparar salidas con la línea base.

## Criterios de aceptación
```gherkin
Escenario: Comportamiento intacto
  Dado la línea base de respuestas capturada antes del refactor
  Cuando consulto los mismos endpoints después del refactor
  Entonces las respuestas son idénticas

Escenario: Ningún controlador accede a datos
  Cuando busco "supabase" o "table(" dentro de app/api/
  Entonces no hay resultados

Escenario: La calificación es pura
  Dado preguntas [{id:1, respuesta_correcta:0},{id:2, respuesta_correcta:1}] y respuestas {"1":0,"2":0}
  Cuando llamo calificar(preguntas, respuestas) en una consola Python
  Entonces obtengo correctas=1, total=2, porcentaje=50, sin tocar la red
```

## Verificación manual
```bash
grep -rnE "supabase|table\(" app/api/ || echo "OK: controladores limpios"
uv run python -c "from app.services.quiz_service import calificar; print(calificar([{'id':1,'respuesta_correcta':0},{'id':2,'respuesta_correcta':1}], {'1':0,'2':0}))"
for r in health bloques lecciones lecciones/1 ejercicios acordes quiz/1; do curl -s localhost:5000/api/$r > despues_$r.json; done
# diff contra la línea base
```

## Definición de hecho específica
- [ ] `app/routes/` y `app/extensions.py` ya no existen.
- [ ] Cada función de controlador ≤ 15 líneas.
- [ ] `verificar_quiz` dividido; ninguna función supera complejidad 10 en ruff (`C901`).
