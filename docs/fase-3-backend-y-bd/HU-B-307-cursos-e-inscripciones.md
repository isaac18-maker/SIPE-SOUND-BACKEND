# HU-B-307 · Modelar cursos e inscripciones

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-306 |
| Rama | `hu/HU-B-307-cursos` |

## Historia
**Como** docente de un colegio
**quiero** crear un curso y compartir un código para que mis estudiantes se unan
**para** seguir el avance de mi grupo sin registrar a cada uno manualmente.

## Alcance
**Incluye**
- Revisión `0007`: `cursos`, `inscripciones`, `curso_bloques`, `retroalimentaciones` según el [modelo objetivo](00-modelo-de-datos-objetivo.md) con sus reglas ON DELETE (docente **RESTRICT**, resto CASCADE / SET NULL) e índices en todas las FK. RLS habilitado **sin** políticas para `anon`/`authenticated` (solo el backend accede).
- Modelos, schemas, repositorios y `CursoService` con:
  - `crear(docente, datos)` → genera `codigo_invitacion` de 8 caracteres sin ambigüedades (sin `0/O/1/I/L`) con `secrets.choice`; reintenta ante colisión.
  - `unirse(estudiante, codigo)` → 404 si no existe o está archivado; idempotente si ya está inscrito.
  - `archivar(docente, curso_id)` → `archivado_en = now()`; 404 si no es su curso.
  - `definir_ruta(docente, curso_id, [{bloque_id, orden}])` → reemplaza `curso_bloques` en una transacción.
- Endpoints de estudiante: `POST /api/v1/cursos/unirse`, `GET /api/v1/cursos` (incluye `docente_nombre` y `retroalimentaciones_sin_leer`).

**No incluye**: endpoints del panel docente (HU-B-310).

## Prompt de ejecución
```text
Ejecuta HU-B-307 en SIPE-SOUND-BACKEND siguiendo el modelo objetivo y la
política de borrado del contrato de BD. La autorización por propiedad
(curso.docente_id == usuario_actual.id) vive en CursoService, no en el controlador.
Un curso ajeno responde 404 (no 403) para no revelar su existencia.
Limita POST /cursos/unirse a 10 intentos por minuto por usuario (flask-limiter,
almacenamiento en memoria por ahora; documenta la limitación).
```

## Criterios de aceptación
```gherkin
Escenario: Unirse con código
  Dado un curso activo con código "K7M2Q9XA"
  Cuando un estudiante envía POST /cursos/unirse {"codigo":"k7m2q9xa"}
  Entonces queda inscrito (el código no distingue mayúsculas)

Escenario: Curso archivado
  Dado un curso archivado
  Cuando un estudiante intenta unirse
  Entonces recibe 404

Escenario: Docente con cursos no se puede borrar
  Dado un docente con un curso
  Cuando se intenta borrar su perfil en la base
  Entonces la operación falla por la FK RESTRICT
```

## Verificación manual
```bash
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
curl -s -X POST -H "Authorization: Bearer $TOKEN_ESTUDIANTE" -H "Content-Type: application/json" \
  -d '{"codigo":"K7M2Q9XA"}' localhost:5000/api/v1/cursos/unirse
```

## Definición de hecho específica
- [ ] `flask-limiter` agregado y justificado en el PR (R4 del contrato).
