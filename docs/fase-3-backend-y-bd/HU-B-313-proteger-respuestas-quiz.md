# HU-B-313 · Proteger las respuestas correctas de los quizzes

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD (corrección de seguridad) |
| Prioridad | Must |
| Estimación | 2 puntos |
| Depende de | HU-B-301, HU-B-303 |
| Rama | `hu/HU-B-313-respuestas-quiz` |
| Origen | Hallazgo crítico de HU-B-206 (`db/legacy/INVENTARIO.md`) |

## Historia
**Como** docente
**quiero** que los estudiantes no puedan leer las respuestas correctas de los quizzes
**para** que aprobar un bloque refleje lo que realmente aprendieron.

## Contexto
La política `Lectura publica quiz_preguntas` (`SELECT using (true)`) y el grant de tabla completa a `anon` permiten leer `respuesta_correcta` con la *anon key*, que es pública:

```
GET https://<proyecto>.supabase.co/rest/v1/quiz_preguntas?select=id,respuesta_correcta
```

El backend oculta la columna en `GET /quiz/{id}`, pero la protección se salta consultando Supabase directamente. No se corrigió antes porque el propio backend leía esa columna con la *anon key* para calificar.

## Alcance
**Incluye**
- `SqlQuizRepository`: el quiz se lee con la conexión del servidor (SQLAlchemy), no con la *anon key*.
- Revisión `0005`: privilegios **por columna** en `quiz_preguntas` para `anon` y `authenticated` (todas las columnas excepto `respuesta_correcta`). `downgrade` restaura el grant de tabla.

**No incluye**: migrar a `evaluaciones` / `preguntas_evaluacion` (HU-B-308).

## Prompt de ejecución
```text
Ejecuta HU-B-313. Primero el repositorio SQL del quiz (respuestas idénticas a las
actuales, verificado contra la base real en solo lectura). Luego la revisión 0005
con revoke/grant por columna. Prueba en base local que, con el rol anon, leer
respuesta_correcta da "permission denied" y leer el resto de columnas funciona.
Orden de despliegue: código antes que la migración.
```

## Criterios de aceptación
```gherkin
Escenario: Respuestas inaccesibles con la anon key
  Dado la revisión 0005 aplicada
  Cuando consulto /rest/v1/quiz_preguntas?select=respuesta_correcta con la anon key
  Entonces recibo un error de permisos y ninguna respuesta

Escenario: El quiz sigue funcionando
  Cuando un estudiante consulta GET /api/v1/quiz/1 y envía POST /api/v1/quiz/1/verificar
  Entonces recibe las preguntas sin respuestas y su calificación, igual que antes

Escenario: Lectura pública del resto de columnas
  Cuando consulto /rest/v1/quiz_preguntas?select=id,pregunta,opciones con la anon key
  Entonces recibo las preguntas
```

## Definición de hecho específica
- [ ] Respuestas de `GET /quiz/{id}` idénticas con el repositorio SQL y con el de Supabase.
- [ ] Verificación en producción con la anon key real: `respuesta_correcta` denegada.
