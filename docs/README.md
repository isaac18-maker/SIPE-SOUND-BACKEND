# Documentación · SIPE-SOUND Backend

Guía de reestructuración del backend organizada en tres fases. Cada HU es un
**prompt ejecutable** por un agente de IA y también una historia de usuario
revisable por el equipo.

## Cómo usar esta carpeta

1. Lee [`00-vision/proyecto.md`](00-vision/proyecto.md) una vez.
2. Toda persona o agente debe conocer la **Fase 1** (contrato) antes de tocar código.
3. Ejecuta las HU de la Fase 2 y la Fase 3 **en el orden de la tabla**, respetando *Depende de*.
4. Para lanzar una HU con un agente, usa el *prompt base* de
   [`01-contrato-ia.md` §6](fase-1-contrato/01-contrato-ia.md#6-prompt-base-para-iniciar-una-hu)
   y luego el bloque *Prompt de ejecución* de la HU.

> Configurar el `.env` (local y producción): [configuracion-entornos.md](configuracion-entornos.md).

## Fase 1 · Contrato para IA generativa

| Documento | Contenido |
|---|---|
| [01-contrato-ia.md](fase-1-contrato/01-contrato-ia.md) | Reglas de trabajo para agentes, flujo, plantilla de PR, commits. |
| [02-arquitectura-backend.md](fase-1-contrato/02-arquitectura-backend.md) | Estructura de carpetas, capas, SOLID con ejemplos. |
| [03-estandares-codigo.md](fase-1-contrato/03-estandares-codigo.md) | Nombres, Ruff, reglas SonarQube, errores, logging. |
| [04-contrato-api.md](fase-1-contrato/04-contrato-api.md) | Formato de respuestas y errores, catálogo de endpoints (**fuente de verdad compartida con el frontend**). |
| [05-contrato-base-datos.md](fase-1-contrato/05-contrato-base-datos.md) | Convenciones, política ON DELETE, sistema de protección de Alembic. |
| [06-plantilla-hu.md](fase-1-contrato/06-plantilla-hu.md) | Plantilla para nuevas HU. |
| [07-definicion-de-hecho.md](fase-1-contrato/07-definicion-de-hecho.md) | DoD, ramas, orden de merge, CI sin pruebas. |

## Fase 2 · Reestructuración (sin cambios funcionales)

| Orden | HU | Pts | Depende de |
|---|---|---|---|
| 1 | [HU-B-201 Higiene del repo y calidad](fase-2-reestructuracion/HU-B-201-higiene-repo-y-calidad.md) | 2 | — |
| 2 | [HU-B-206 Inventario del esquema real](fase-2-reestructuracion/HU-B-206-inventario-esquema-real.md) | 2 | 201 |
| 3 | [HU-B-202 Configuración y app factory](fase-2-reestructuracion/HU-B-202-configuracion-y-app-factory.md) | 3 | 201 |
| 4 | [HU-B-203 Capas y reubicación](fase-2-reestructuracion/HU-B-203-capas-y-reubicacion.md) | 5 | 202 |
| 5 | [HU-B-204 Errores, respuestas y `/api/v1`](fase-2-reestructuracion/HU-B-204-errores-respuestas-y-versionado.md) | 3 | 203 |
| 6 | [HU-B-205 Módulo de seguridad](fase-2-reestructuracion/HU-B-205-modulo-seguridad.md) | 3 | 204 |

## Fase 3 · Backend, base de datos y panel docente

Referencia: [modelo de datos objetivo](fase-3-backend-y-bd/00-modelo-de-datos-objetivo.md).
Los números de migración de las HU 307 en adelante se recalculan al implementarlas (se insertaron 0005 y 0008).

| Orden | HU | Pts | Depende de | Migraciones |
|---|---|---|---|---|
| 1 | [HU-B-301 SQLAlchemy y modelos base](fase-3-backend-y-bd/HU-B-301-sqlalchemy-y-modelos-base.md) | 5 | 203, 206 | — |
| 2 | [HU-B-302 Alembic con protecciones](fase-3-backend-y-bd/HU-B-302-alembic-con-protecciones.md) | 5 | 301 | — |
| 3 | [HU-B-303 Migración baseline](fase-3-backend-y-bd/HU-B-303-migracion-baseline.md) | 3 | 302 | 0001 |
| 4 | [HU-B-304 Roles y autorización](fase-3-backend-y-bd/HU-B-304-roles-y-autorizacion.md) | 3 | 303, 205 | 0002 |
| 5 | [HU-B-305 Progreso con integridad](fase-3-backend-y-bd/HU-B-305-progreso-con-integridad.md) | 5 | 304 | 0003, 0004 |
| 6 | [HU-B-306 Contenido editable](fase-3-backend-y-bd/HU-B-306-contenido-editable.md) | 5 | 305 | 0006, 0007 |
| 7 | [HU-B-307 Cursos e inscripciones](fase-3-backend-y-bd/HU-B-307-cursos-e-inscripciones.md) | 3 | 306 | 0011 |
| 8 | [HU-B-308 Evaluaciones e intentos](fase-3-backend-y-bd/HU-B-308-evaluaciones-e-intentos.md) | 8 | 307 | 0015, 0016 |
| 9 | [HU-B-309 API docente: contenido](fase-3-backend-y-bd/HU-B-309-api-docente-contenido.md) | 5 | 306, 304 | — |
| 10 | [HU-B-310 API docente: cursos y estudiantes](fase-3-backend-y-bd/HU-B-310-api-docente-cursos-y-estudiantes.md) | 8 | 307, 308 | — |
| 11 | [HU-B-311 API docente: evaluaciones](fase-3-backend-y-bd/HU-B-311-api-docente-evaluaciones.md) | 5 | 308, 310 | — |
| 12 | [HU-B-312 Retroalimentación y retiro de legado](fase-3-backend-y-bd/HU-B-312-retroalimentacion-y-retiro-legado.md) | 5 | 308, 310 | 0017 (destructiva aprobada) |
| 6.1 | [HU-B-313 Proteger respuestas de quizzes](fase-3-backend-y-bd/HU-B-313-proteger-respuestas-quiz.md) 🔴 seguridad | 2 | 301, 303 | 0005 |
| 6.2 | [HU-B-314 Retirar tabla partituras](fase-3-backend-y-bd/HU-B-314-retirar-partituras.md) | 1 | 303 | 0008 (destructiva aprobada) |
| 6.3 | [HU-B-315 Una sola conexión (Session pooler)](fase-3-backend-y-bd/HU-B-315-una-sola-conexion.md) | 3 | 305, 313 | — |
| 6.4 | [HU-B-316 Corrección de riesgos](fase-3-backend-y-bd/HU-B-316-correccion-de-riesgos.md) 🔴 seguridad | 5 | 315 | 0009, 0010 |
| 7.1 | [HU-B-317 Respuesta estándar y Swagger](fase-3-backend-y-bd/HU-B-317-respuesta-estandar.md) | 3 | 204, 307 | — |
| 7.2 | [HU-B-318 Registro e invitaciones](fase-3-backend-y-bd/HU-B-318-registro-de-cuentas.md) | 5 | 304, 317 | — |
| 7.3 | [HU-B-319 Retiro inmediato del legado](fase-3-backend-y-bd/HU-B-319-retiro-del-legado.md) | 3 | 317 | 0012 (destructiva aprobada) |
| 7.4 | [HU-B-320 Límites de los campos](fase-3-backend-y-bd/HU-B-320-limites-de-campos.md) | 3 | 319 | 0013 |
| 7.5 | [HU-B-321 Cuentas sin clave service_role](fase-3-backend-y-bd/HU-B-321-registro-sin-service-role.md) | 3 | 320 | 0014 |
| 7.6 | [HU-B-322 Autenticación a través del backend](fase-3-backend-y-bd/HU-B-322-autenticacion-por-backend.md) | 5 | 321 | — |

## Relación con el frontend

Las HU del frontend (`SIPE-SOUND-FULLSTACK/docs/`) que consumen estas APIs:

| Backend | Frontend |
|---|---|
| HU-B-204 (`/api/v1`) | HU-F-203 (cliente HTTP) |
| HU-B-304 (`/me`, roles) | HU-F-204 (sesión), HU-F-303 (navegación por rol) |
| HU-B-322 (`/auth/*`) | HU-F-207 (autenticación por el backend) |
| HU-B-305, HU-B-308 | HU-F-304 (ruta), HU-F-306 (evaluación y progreso) |
| HU-B-312 | HU-F-311 (retroalimentación) |
| HU-B-307 | HU-F-311 (unirse a curso) |
| HU-B-309 | HU-F-308 (contenido docente) |
| HU-B-310 | HU-F-307 (cursos), HU-F-309 (estudiantes) |
| HU-B-311 | HU-F-310 (evaluaciones docente) |
