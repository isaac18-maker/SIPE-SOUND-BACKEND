# HU-B-324 · Exponer la actividad del estudiante para su inicio

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Should |
| Estimación | 3 puntos |
| Depende de | HU-B-305 (progreso), HU-B-308 (intentos) |
| Rama | `hu/HU-B-324-actividad-estudiante` |
| Relacionada | HU-F-315 (inicio del estudiante), HU-F-317 (gráfico de práctica) |

## Historia
**Como** estudiante
**quiero** que la plataforma me muestre lo último que practiqué y cómo ha sido mi práctica en las últimas semanas
**para** retomar donde quedé y ver que mi constancia da resultado.

## Contexto
El rediseño del frontend (HU-F-315, HU-F-317) añade un inicio con actividad reciente y un gráfico de
práctica. Hoy la API solo da:

- `GET /progreso/resumen`: totales y `ultimo_avance` (una sola fecha).
- `GET /evaluaciones/{id}/intentos`: el historial de **una** evaluación, por lo que el frontend hace una
  petición por bloque para armar la actividad.

Las fechas ya existen en la base (`progreso_lecciones.actualizado_en`,
`progreso_ejercicios.actualizado_en`, `intentos_evaluacion.creado_en`); solo falta exponerlas.
**No hace falta ninguna migración.**

Limitaciones que esta HU **no** resuelve y que el frontend no debe simular:
- No se guarda el **tiempo de práctica** ni las visitas a una lección; solo el último cambio de
  avance por contenido. La actividad cuenta *registros de avance*, no minutos.
- Una lección completada dos veces conserva solo la última fecha (`actualizado_en`).

## Alcance
**Incluye**
- `GET /progreso/actividad?dias=28` (🎓). `dias` es un entero de 7 a 90 (por defecto 28). Responde:
  ```json
  {
    "recientes": [
      { "tipo": "leccion",    "id": 12, "titulo": "Cambio entre Em y Am", "bloque_id": 2, "fecha": "2026-10-20T14:05:00Z", "completado": true },
      { "tipo": "ejercicio",  "id": 7,  "titulo": "Rasgueo abajo-arriba", "bloque_id": 2, "fecha": "2026-10-19T22:10:00Z", "completado": false, "mejor_bpm": 72 },
      { "tipo": "evaluacion", "id": 3,  "titulo": "Evaluación del bloque 2", "bloque_id": 2, "fecha": "2026-10-18T16:40:00Z", "puntaje": 60, "aprobado": false }
    ],
    "por_dia": [ { "fecha": "2026-09-26", "registros": 0 }, "…", { "fecha": "2026-10-23", "registros": 3 } ],
    "dias_con_practica": 9
  }
  ```
  - `recientes`: los 10 eventos más recientes, mezclados y ordenados por `fecha` descendente.
  - `por_dia`: un elemento por día del rango, **incluidos los días en cero**, en la zona horaria
    `America/Bogota`, del más antiguo al más reciente.
  - `dias_con_practica`: días del rango con al menos un registro.
- `GET /ruta` (🌐🎓) añade a cada bloque `acordes: string[]`: los acordes distintos de sus lecciones
  publicadas, en orden de lección, máximo 6. El frontend los usa como miniatura del bloque (diagrama
  del primer acorde), que así corresponde al contenido real.
- Contrato 04 (§ catálogo de endpoints y el ejemplo de respuesta) actualizado.

**No incluye**: registrar tiempo de práctica o visitas (requiere migración y decisión del equipo; HU
futura), logros o rachas.

## Prompt de ejecución
```text
Ejecuta HU-B-324 en SIPE-SOUND-BACKEND. Sin migraciones. La consulta de
actividad va en el repositorio de progreso con SQL que agrupe por
(fecha AT TIME ZONE 'America/Bogota')::date y complete los días vacíos con
generate_series. Valida ?dias con el esquema de entrada (7–90) y responde 400
VALIDACION fuera de rango. Solo los contenidos publicados aparecen con título;
si el contenido se archivó, el evento se conserva con su título actual.
Añade `acordes` a GET /ruta sin aumentar el número de consultas por bloque
(una consulta agregada para toda la ruta).
```

## Criterios de aceptación
```gherkin
Escenario: Actividad reciente mezclada
  Dado que completé una lección hoy y presenté una evaluación ayer
  Cuando consulto GET /progreso/actividad
  Entonces el primer elemento de recientes es la lección y el segundo la evaluación

Escenario: Días sin práctica
  Dado que no registré avance en los últimos 28 días
  Entonces por_dia tiene 28 elementos con registros 0 y dias_con_practica es 0

Escenario: Rango inválido
  Cuando consulto ?dias=365
  Entonces recibo 400 VALIDACION con "dias: debe estar entre 7 y 90."

Escenario: Acordes del bloque
  Dado un bloque cuyas lecciones usan Em, Am y Em
  Cuando consulto GET /ruta
  Entonces el bloque trae acordes ["Em", "Am"]
```

## Orden de merge
Backend primero. HU-F-315 funciona sin esta HU (muestra solo lo que ya da `/progreso/resumen` y los
intentos); HU-F-317 sí la necesita.
