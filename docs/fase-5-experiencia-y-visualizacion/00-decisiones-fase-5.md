# Fase 5 · Experiencia y visualización: decisiones

> Referencia para HU-B-501 … HU-B-503 y para sus pares del frontend (HU-F-501 … HU-F-507,
> en `SIPE-SOUND-FULLSTACK/docs/fase-5-experiencia-y-visualizacion/`). Si una HU de esta fase
> contradice el contrato de `docs/fase-1-contrato/`, gana el contrato y el agente lo reporta.
> Propuesta del equipo del 2026-10-25, pendiente de priorizar.

## 1. Qué resuelve la fase

La fase 4 dejó todas las funciones. La fase 5 mejora **cómo se ven y cómo se recorren**: más
visual, con menos clics y con el avance siempre identificable.

| Necesidad | HU frontend | HU backend |
|---|---|---|
| Mensajes con diseño de chat profesional | F-501 | — (usa HU-B-409) |
| "Mi progreso" con gráficos claros: a qué corresponde cada avance | F-502 | — (usa `/progreso/*`, `/ruta`) |
| Ejercicios como tarjetas y filtro por estado de avance | F-503 | **B-501** |
| "Mis cursos" visible en el menú, con avance y estado por curso, ligado a la ruta | F-504 | **B-502** |
| Docente: cursos como tarjetas y estudiantes en pocos clics | F-505 | — (usa `/docente/progreso`) |
| Panel de progreso del docente con gráficas, filtros y evaluaciones habilitables | F-506 | **B-503** |
| Barra superior con perfil y cerrar sesión; menú lateral contraíble y recordado | F-507 | — |

Corregidos fuera de HU (2026-10-25): el 429 al enviar la solicitud de cambio de nombre
(`/me/solicitud-nombre` leía el rol del token en vez del de la base) y el modo "Tema del sistema".

## 2. Decisiones

1. **El estado de avance lo calcula el backend, una sola vez.** El frontend no recalcula
   porcentajes ni estados a partir de listas largas: recibe `avance_pct` y un estado de tres
   valores (`sin_iniciar`, `en_curso`, `finalizado`). Así las tarjetas, los filtros y los gráficos
   coinciden entre pantallas.
2. **Regla del estado** (igual para ejercicios, cursos y bloques):

   | Estado | Significa |
   |---|---|
   | `sin_iniciar` | Ningún registro de avance |
   | `en_curso` | Al menos un registro y no todo completado |
   | `finalizado` | Todo lo que lo compone está completado (y, en un curso, sus bloques con evaluación aprobados) |

3. **Los gráficos son SVG propios, sin librería** (contrato 02 §2: no sumar dependencias para
   algo que se resuelve con 60 líneas). Cada gráfico lleva una **alternativa en tabla** (contrato
   05 §6) y sus colores salen de tokens, nunca solo color: también texto y forma.
4. **Sin tiempo real con websockets.** El chat consulta el hilo abierto cada 15 s mientras la
   pestaña esté visible; el contador de la navegación sigue cada 60 s (HU-F-407).
5. **Habilitar o deshabilitar una evaluación** es publicar o cerrar (`PATCH /docente/evaluaciones/{id}/estado`,
   ya existe). No se agregan excepciones por estudiante en esta fase.

## 3. Fuera de alcance de la fase

- Notificaciones del navegador, sonidos o correos por mensajes nuevos.
- Exportar a PDF y reportes programados.
- Excepciones de evaluación por estudiante.
