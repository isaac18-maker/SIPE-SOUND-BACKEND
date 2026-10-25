# HU-B-503 · Series y distribuciones para el panel del docente

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-408 |
| Rama | `hu/HU-B-503-series-del-panel-docente` |
| Relacionada | HU-F-506 |
| Referencia | [00-decisiones-fase-5.md](00-decisiones-fase-5.md) §2 y §3 |

## Historia
**Como** docente
**quiero** ver la actividad de mi curso en el tiempo, cómo se reparte el avance y cómo van las evaluaciones
**para** entender de un vistazo qué pasa con el grupo sin abrir estudiante por estudiante.

## Contexto
- HU-B-408 entrega totales por curso, la matriz y "necesitan apoyo", pero ninguna serie en el
  tiempo ni distribución: sin eso un gráfico tendría que inventarse en el cliente.

## Alcance
**Incluye**
1. `GET /docente/progreso/series?curso_id=&dias=` (`dias` 7–90, 28 por defecto; `curso_id`
   opcional = todos mis cursos activos; el admin puede pasar `docente_id`):
   - `actividad_por_dia`: `[{fecha, estudiantes_activos, registros}]` (días vacíos incluidos,
     zona America/Bogota, como `/progreso/actividad`).
   - `distribucion_avance`: `[{desde, hasta, estudiantes}]` en cinco tramos de 20 % (0–19 … 80–100).
   - `estados`: `{sin_iniciar, en_curso, finalizado}` (conteo de estudiantes, regla de decisiones §2).
   - `evaluaciones`: por evaluación del curso `{evaluacion_id, titulo, estado, bloque_id, intentos, aprobados, promedio_puntaje}`
     (sin respuestas correctas).
2. Filtros opcionales sobre todo lo anterior: `?bloque_id=` y `?estudiantes=al_dia|sin_actividad|en_riesgo`
   (mismas definiciones que HU-B-408: 7 y 14 días y reprobados repetidos).
3. Un docente solo ve lo suyo (404 en curso ajeno); el admin, todo. Sin correos ni apellidos
   en los agregados.
4. Contrato 04 §4.3 y §5.

**No incluye**
- Series por estudiante (ya está en el detalle de HU-B-408).
- Comparar contra otros docentes.

## Prompt de ejecución
```text
Ejecuta HU-B-503 en SIPE-SOUND-BACKEND. Agrega GET /docente/progreso/series con actividad_por_dia,
distribucion_avance (5 tramos), estados (sin_iniciar/en_curso/finalizado) y evaluaciones con
intentos, aprobados y promedio, filtrable por curso_id, bloque_id, dias y estudiantes=
al_dia|sin_actividad|en_riesgo. Reutiliza las definiciones y el alcance de HU-B-408. Sin
correos. Sin N+1.
```

## Pasos
1. Consultas agregadas (una por serie) reutilizando el alcance de HU-B-408.
2. Esquemas de entrada y salida; límites de `dias`.
3. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Actividad
  Dado un curso con registros de avance en tres días distintos
  Cuando consulto series?curso_id=1&dias=28
  Entonces actividad_por_dia trae 28 entradas y las de esos tres días con registros > 0

Escenario: Distribución
  Dado 10 estudiantes con distintos avances
  Entonces la suma de distribucion_avance[].estudiantes es 10

Escenario: Evaluaciones
  Cuando consulto series de un curso con dos evaluaciones
  Entonces evaluaciones trae sus intentos, aprobados y promedio, y ninguna respuesta correcta

Escenario: Curso ajeno
  Cuando un docente consulta series de un curso de otro docente
  Entonces recibe 404
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
# Con el seed: comparar estados y distribución contra la matriz de HU-B-408.
```

## Definición de hecho específica
- [ ] Las sumas cuadran con `/docente/progreso` y la matriz (mismo curso, mismo día).
- [ ] Ninguna respuesta correcta ni correo en la respuesta.
