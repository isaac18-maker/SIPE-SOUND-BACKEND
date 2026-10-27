# HU-B-409 · Mensajería interna y avisos

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 8 puntos |
| Depende de | HU-B-405, HU-B-307 |
| Rama | `hu/HU-B-409-mensajeria` |
| Relacionada | HU-F-407 |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §6 |

## Historia
**Como** administrador o docente
**quiero** enviar avisos a una persona, a un curso o a todos los estudiantes o docentes
**para** comunicar fechas, cambios y recordatorios dentro de la plataforma;
**y como** estudiante **quiero** escribirle a mi docente **para** resolver dudas sin salir de SIPE-SOUND.

## Contexto
- Solo existe la retroalimentación docente → estudiante por curso (`retroalimentaciones`, B-310/312),
  sin respuesta posible.
- No hay avisos generales ni forma de que el estudiante escriba a su docente.

## Modelo (revisión `0025_mensajeria`, esquema)

| Tabla | Columnas | Reglas |
|---|---|---|
| `mensajes` | `id uuid`, `remitente_id` (FK `profiles` **SET NULL**), `asunto` (3–120), `cuerpo` (1–4000), `alcance` (`usuario`, `curso`, `estudiantes_docente`, `rol_estudiante`, `rol_docente`, `rol_admin`, `todos`), `curso_id` (FK `cursos` **SET NULL**, null salvo alcance `curso`), `respuesta_a_id` (FK `mensajes` SET NULL), `hilo_id uuid` (el id del primer mensaje), `creado_en` | CHECK de largos y de alcance; índice `(hilo_id, creado_en)` y `(remitente_id, creado_en desc)` |
| `mensaje_destinatarios` | `mensaje_id` (FK CASCADE), `destinatario_id` (FK `profiles` CASCADE), `leido_en`, `archivado_en` | PK `(mensaje_id, destinatario_id)`; índice `(destinatario_id, leido_en, mensaje_id)` |

- RLS activado sin políticas en ambas tablas.
- Al enviar a un grupo se copian los destinatarios **en ese momento** con un solo
  `INSERT … SELECT` (quien entra después al curso no ve avisos viejos).
- El remitente también se agrega como destinatario con `leido_en = now()` para que el hilo
  aparezca en su bandeja cuando le respondan.

## Alcance
**Incluye**
1. Reglas de destino (00-decisiones §6) en `MensajeriaService.validar_destino`, un solo lugar:

   | Remitente | `alcance` permitidos |
   |---|---|
   | admin | `usuario` (cualquiera), `rol_estudiante`, `rol_docente`, `rol_admin`, `todos` |
   | docente | `usuario` (estudiante inscrito en un curso activo suyo, cualquier docente o admin), `curso` (suyo y activo), `estudiantes_docente` (todos sus estudiantes), `rol_docente`, `rol_admin` |
   | estudiante | `usuario` solo si es docente de un curso activo donde está inscrito |

   Responder (`respuesta_a_id`) va **solo** al remitente del mensaje original y aplica las mismas
   reglas: un estudiante puede responder a su docente, no a un aviso del admin. Las cuentas
   suspendidas o sin verificar no reciben avisos de grupo.
2. Rutas (prefijo `/api/v1`, cualquier rol con sesión):

   | Método | Ruta | Detalle |
   |---|---|---|
   | POST | `/mensajes` | `{alcance, destinatario_id?, curso_id?, asunto, cuerpo, respuesta_a_id?}` → 201 `{id, hilo_id, destinatarios: N}`. 403 si el destino no está permitido; 422 si el grupo está vacío. Respuesta a un hilo: el `asunto` se toma del original. |
   | GET | `/mensajes` | Bandeja de **hilos** (último mensaje por hilo), paginada, `?filtro=recibidos\|enviados\|no_leidos\|archivados`, `?q=` (asunto). Cada hilo: `hilo_id`, `asunto`, `ultimo` (`remitente`, `extracto` 140, `creado_en`), `no_leidos`, `alcance`, `curso`. |
   | GET | `/mensajes/hilos/{hilo_id}` | Mensajes del hilo que el usuario recibió o envió, en orden, y `puede_responder` (calculado con las mismas reglas de destino). Marca como leídos los suyos. 404 si no participa. |
   | PATCH | `/mensajes/hilos/{hilo_id}` | `{archivado: bool}` o `{leido: false}`. |
   | GET | `/mensajes/no-leidos` | `{total}` (para el contador; consulta por índice, < 10 ms). |
   | GET | `/mensajes/destinatarios` | `?q=` (2–80). Personas y grupos a los que **este** usuario puede escribir, máx. 20: `{tipo: usuario\|curso\|grupo, id, etiqueta, detalle}`. El estudiante ve solo sus docentes con el nombre del curso. |
3. Datos que se muestran: remitente con `nombre`, `apellido` y `rol`; **nunca** correos.
4. Límites: estudiante 20 mensajes/hora, docente 60/hora, admin 120/hora; avisos de grupo
   (`alcance` ≠ `usuario`): 10/hora por remitente. **Se miden en la base** (se cuentan los
   mensajes reales de la última hora, `MensajeriaService`), no en `app/core/limites.py`: el
   limitador de Flask vive en memoria de cada proceso y se perdería con varios procesos o al
   reiniciar. Constantes en `app/core/constants.py`.
5. Contrato 04 (nueva sección 4.5 Mensajería, §7 `asunto` 3–120 y `cuerpo` 1–4000) y contrato 05
   (tabla ON DELETE).

**No incluye**
- Correos ni notificaciones push por cada mensaje (00-decisiones §6).
- Tiempo real (WebSocket): el frontend consulta `/mensajes/no-leidos` cada 60 s.
- Adjuntos, edición o borrado de mensajes enviados.
- Unificar `retroalimentaciones` con mensajes (se anota como posible HU).

## Prompt de ejecución
```text
Ejecuta HU-B-409 en SIPE-SOUND-BACKEND. Crea la mensajería interna: tablas mensajes y
mensaje_destinatarios (revisión 0025, RLS sin políticas). Las reglas de quién puede escribir a
quién viven solo en MensajeriaService y siguen la tabla de la HU: el estudiante solo escribe a
los docentes de sus cursos activos y solo responde a ellos. Los envíos a grupos copian los
destinatarios con un único INSERT … SELECT. Nunca devuelvas correos. No envíes correos por
mensajes. Límites por rol en app/core/limites.py. Capas: api → services → repositories.
```

## Pasos
1. Revisión 0025 con `downgrade()`; modelos y repositorio.
2. `MensajeriaService` (reglas de destino, envío, respuestas, bandeja, lectura).
3. Rutas y límites.
4. Contratos 04 y 05.

## Criterios de aceptación
```gherkin
Escenario: Aviso a todos los estudiantes
  Cuando el admin envía un mensaje con alcance "rol_estudiante"
  Entonces cada estudiante activo lo ve en GET /mensajes con no_leidos = 1

Escenario: Docente a su curso
  Cuando un docente envía un aviso con alcance "curso" a su curso 3
  Entonces lo reciben solo los inscritos en el curso 3

Escenario: Docente a curso ajeno
  Cuando un docente envía un aviso al curso de otro docente
  Entonces recibe 403

Escenario: Estudiante a su docente
  Dado un estudiante inscrito en el curso del docente D
  Cuando escribe a D
  Entonces recibe 201 y D lo ve en su bandeja

Escenario: Estudiante a otra persona
  Cuando un estudiante intenta escribir a otro estudiante, a un admin o a un docente que no es suyo
  Entonces recibe 403 "Solo puedes escribirle a los docentes de tus cursos."

Escenario: Responder un aviso del admin
  Cuando un estudiante responde un aviso del admin
  Entonces recibe 403

Escenario: Hilo
  Dado que el docente responde el mensaje del estudiante
  Cuando el estudiante abre el hilo
  Entonces ve los dos mensajes en orden y el contador baja a 0

Escenario: Sin correos
  Cuando cualquier usuario pide GET /mensajes o GET /mensajes/destinatarios
  Entonces ninguna respuesta contiene un campo email
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
curl -s -X POST localhost:5000/api/v1/mensajes -H "Authorization: Bearer $TOKEN_DOCENTE" \
  -H "Content-Type: application/json" \
  -d '{"alcance":"curso","curso_id":3,"asunto":"Ensayo del viernes","cuerpo":"Traigan la guitarra afinada."}'
```

## Definición de hecho específica
- [ ] Aviso a 500 estudiantes: una sola sentencia de inserción de destinatarios (medición en el PR).
- [ ] `GET /mensajes/no-leidos` usa el índice `(destinatario_id, leido_en, …)` (EXPLAIN en el PR).
- [ ] Las reglas de destino están en un único método, cubiertas por los escenarios de arriba.
