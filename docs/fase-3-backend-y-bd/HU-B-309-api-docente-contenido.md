# HU-B-309 · API del panel docente: gestionar lecciones y ejercicios

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-306, HU-B-304 |
| Rama | `hu/HU-B-309-docente-contenido` |

## Historia
**Como** docente
**quiero** crear, editar, publicar, archivar y eliminar lecciones y ejercicios
**para** adaptar el contenido al ritmo de mi grupo.

## Alcance
**Incluye** los endpoints `/api/v1/docente/lecciones*` y `/api/v1/docente/ejercicios*` del [contrato de API §4.3](../fase-1-contrato/04-contrato-api.md#43-nuevos--panel-docente-fase-3-prefijo-docente):
- Listado con filtros `?estado=&bloque_id=&q=` y paginación.
- Crear (estado inicial `borrador`, `autor_id = usuario actual`).
- Editar (`PATCH`): solo el autor o un admin.
- Cambiar estado: `borrador → publicado → archivado`, y `archivado → borrador`.
- Eliminar: si hay progreso registrado → `409 CONFLICTO` con `details.sugerencia = "archivar"`; si no, borrado físico (la cascada limpia `leccion_acordes`; los ejercicios quedan con `leccion_id` nulo).
- Schemas Pydantic con límites: `titulo` 3–120, `descripcion` ≤ 2000, `bpm_recomendado` 30–240, `compas` en (`2/4`,`3/4`,`4/4`,`6/8`), `pasos` ≤ 20 elementos de ≤ 300 caracteres, `acordes` deben existir en la tabla `acordes`.

**No incluye**: subida de archivos/imágenes/audio.

## Prompt de ejecución
```text
Ejecuta HU-B-309 en SIPE-SOUND-BACKEND.
- Blueprint app/api/v1/docente/contenido.py con @roles_required("docente","admin").
- Servicios ContenidoLeccionService y ContenidoEjercicioService (o uno genérico
  con estrategia por tipo si evita duplicación > 3 %, Sonar). Sin lógica en controladores.
- La máquina de estados de "estado" se define en un único diccionario de
  transiciones permitidas; una transición inválida responde 422.
- Contenido ajeno: 404. Un admin puede editar todo.
- Sanitiza texto: quita espacios extremos; no aceptes HTML (rechaza "<" y ">" en titulo).
```

## Criterios de aceptación
```gherkin
Escenario: Crear como borrador
  Cuando un docente crea una lección
  Entonces su estado es "borrador" y no aparece en GET /api/v1/lecciones

Escenario: Eliminar con progreso
  Dado una lección con progreso de un estudiante
  Cuando el docente la elimina
  Entonces recibe 409 con sugerencia "archivar"
  Y la lección sigue existiendo

Escenario: Eliminar sin progreso
  Dado una lección sin progreso
  Cuando el docente la elimina
  Entonces recibe 204 y sus relaciones dependientes se limpian por cascada

Escenario: Contenido ajeno
  Dado una lección de otro docente
  Cuando intento editarla
  Entonces recibo 404
```

## Verificación manual
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN_DOCENTE" -H "Content-Type: application/json" \
  -d '{"bloque_id":1,"numero":4,"titulo":"Rasgueo básico","nivel":"principiante","duracion_min":20}' \
  localhost:5000/api/v1/docente/lecciones
```

## Definición de hecho específica
- [ ] Duplicación entre lecciones y ejercicios ≤ 3 % (SonarLint).
