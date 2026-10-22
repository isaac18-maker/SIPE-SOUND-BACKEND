# 01 · Contrato de trabajo para IA generativa (Backend)

> Este documento es **vinculante**. Cualquier agente (Claude Code, Copilot,
> Cursor, ChatGPT, etc.) que genere código en este repositorio debe cumplirlo.
> El punto de entrada para los agentes es [`AGENTS.md`](../../AGENTS.md).

## 1. Orden de lectura obligatorio

Antes de escribir una sola línea, el agente lee en este orden:

1. [`00-vision/proyecto.md`](../00-vision/proyecto.md) — para qué existe el producto.
2. Este documento.
3. [`02-arquitectura-backend.md`](02-arquitectura-backend.md) — dónde va cada cosa.
4. [`03-estandares-codigo.md`](03-estandares-codigo.md) — cómo se escribe.
5. [`04-contrato-api.md`](04-contrato-api.md) — forma de las respuestas y endpoints.
6. [`05-contrato-base-datos.md`](05-contrato-base-datos.md) — reglas de BD y Alembic.
7. La HU que se va a ejecutar, **completa**, incluyendo sus dependencias.

Si la HU contradice el contrato, **gana el contrato** y el agente lo reporta.

## 2. Reglas de ejecución

| # | Regla |
|---|---|
| R1 | **Una HU = una rama = un PR.** Rama: `hu/HU-B-XXX-descripcion-corta`. |
| R2 | **Alcance cerrado.** Solo se modifica lo que la HU lista en *Alcance*. Lo que se encuentre fuera se anota en *Hallazgos* del PR, no se corrige. |
| R3 | **Dependencias primero.** Si una HU listada en *Depende de* no está terminada, el agente se detiene y lo informa. |
| R4 | **Sin dependencias nuevas no autorizadas.** Solo se instalan paquetes nombrados en la HU. Cualquier otro requiere justificación en el PR. |
| R5 | **Fase 2 = refactor sin cambio funcional.** Los endpoints responden lo mismo antes y después (salvo que la HU diga lo contrario). |
| R6 | **Migraciones inmutables.** Nunca se edita un archivo de `migrations/versions/` que ya esté en `main`. Se crea una nueva revisión. |
| R7 | **Secretos.** Nunca se lee, imprime, copia ni commitea `.env`. Las variables nuevas se documentan en `.env.example` con valores falsos. |
| R8 | **Sin pruebas unitarias en esta etapa.** Es una decisión del equipo para las fases 1–3. El código sí debe ser *testeable* (inyección de dependencias, funciones puras en servicios). |
| R9 | **Verificación manual obligatoria.** Cada HU trae una sección *Verificación manual*; el agente la ejecuta (o explica por qué no pudo) y pega el resultado en el PR. |
| R10 | **Idioma.** Documentación, comentarios, mensajes de error al usuario y commits en **español**. Identificadores según [`03-estandares-codigo.md`](03-estandares-codigo.md). |
| R11 | **Ambigüedad = pregunta.** Si un paso admite dos interpretaciones con efectos distintos, el agente pregunta antes de elegir. |
| R12 | **No borrar datos.** Ninguna HU autoriza `DROP`/`TRUNCATE`/`DELETE` masivo sobre datos reales sin la marca de aprobación descrita en el contrato de BD. |

## 3. Flujo de trabajo por HU

```
leer contrato → leer HU → verificar dependencias → crear rama
   → implementar paso a paso (commits pequeños)
   → ejecutar linters (ruff) y verificación manual
   → abrir PR con la plantilla de entrega
```

## 4. Plantilla de entrega (cuerpo del PR)

```markdown
## HU-B-XXX · <título>

### Resumen
<2–4 líneas de qué se hizo>

### Archivos
- creados: ...
- movidos: origen → destino
- modificados: ...
- eliminados: ...

### Verificación manual
<comandos ejecutados y salida relevante>

### Checklist DoD
- [ ] ruff check sin errores
- [ ] ruff format aplicado
- [ ] Sin secretos ni .env en el diff
- [ ] Criterios de aceptación cumplidos (uno por uno)
- [ ] .env.example actualizado si aplica
- [ ] Documentación actualizada si cambió un contrato

### Hallazgos fuera de alcance
<deuda técnica detectada, sin corregir>
```

## 5. Commits

Formato *Conventional Commits* en español, con la HU al final:

```
feat(docente): listar estudiantes de un curso [HU-B-309]
refactor(core): mover configuracion a app/core/config.py [HU-B-202]
fix(quiz): no rebajar el mejor puntaje en reintentos [HU-B-307]
chore(migraciones): crear revision baseline [HU-B-303]
```

Tipos permitidos: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `perf`, `build`, `ci`.

## 6. Prompt base para iniciar una HU

Copie y pegue esto en el agente, cambiando el identificador:

```text
Eres un desarrollador backend senior en el repositorio SIPE-SOUND-BACKEND
(Flask + Supabase/PostgreSQL). Lee AGENTS.md y todos los documentos de
docs/fase-1-contrato/ antes de empezar. Luego ejecuta la historia
docs/<fase>/HU-B-XXX-*.md paso a paso, respetando su alcance.
No escribas pruebas unitarias. Al terminar, entrega el cuerpo del PR
con la plantilla de la sección 4 del contrato de IA.
```

## 7. Qué hacer cuando algo falla

- **Un paso de la HU es imposible** (archivo no existe, API cambió): detenerse, explicar y proponer un ajuste a la HU. No improvisar.
- **Un linter falla por código previo fuera del alcance**: no corregirlo; usar `# noqa: <regla>` *solo* si la HU lo autoriza, si no, reportarlo.
- **Una migración falla en local**: `alembic downgrade -1`, corregir la revisión *no publicada* y repetir. Nunca `--sql` manual contra producción.
