"""copiar quizzes por bloque y sus resultados a evaluaciones e intentos

HU: HU-B-308
Revision ID: 0016
Revises: 0015
Create Date: 2026-10-24 13:10:00+00:00
Tipo: datos
Destructiva: no

1. Por cada bloque con preguntas en quiz_preguntas -> una evaluacion global publicada
   ("Evaluacion del bloque N", aprobacion 80 %).
2. Preguntas: pregunta -> enunciado, opciones text[] -> jsonb, orden_index -> orden (1..n).
3. progreso tipo 'bloque' -> un intento: puntaje = porcentaje, aprobado = completado,
   respuestas '{}' (el detalle no existia), correctas estimadas con el puntaje.
Idempotente: cada paso omite lo que ya existe. No borra nada (lo retira HU-B-312).
Datos de produccion medidos el 2026-10-24: 18 preguntas en 6 bloques, 3 resultados.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CREAR_EVALUACIONES = """
insert into public.evaluaciones (titulo, bloque_id, porcentaje_aprobacion, estado)
select 'Evaluación del bloque ' || b.numero, b.id, 80, 'publicada'
from public.bloques b
where exists (select 1 from public.quiz_preguntas q where q.bloque_id = b.id)
  and not exists (
    select 1 from public.evaluaciones e where e.bloque_id = b.id and e.curso_id is null)
"""

COPIAR_PREGUNTAS = """
insert into public.preguntas_evaluacion
  (evaluacion_id, enunciado, opciones, respuesta_correcta, orden)
select e.id, btrim(q.pregunta), to_jsonb(q.opciones), q.respuesta_correcta,
       row_number() over (partition by e.id order by q.orden_index, q.id)
from public.quiz_preguntas q
join public.evaluaciones e on e.bloque_id = q.bloque_id and e.curso_id is null
where not exists (select 1 from public.preguntas_evaluacion p where p.evaluacion_id = e.id)
"""

COPIAR_RESULTADOS = """
insert into public.intentos_evaluacion
  (evaluacion_id, estudiante_id, puntaje, correctas, total, aprobado, respuestas, creado_en)
select e.id, p.usuario_id, p.porcentaje, round(p.porcentaje * n.total / 100.0), n.total,
       coalesce(p.completado, false), '{}'::jsonb, coalesce(p.actualizado_en, now())
from public.progreso p
join public.evaluaciones e on e.bloque_id = p.contenido_id and e.curso_id is null
join (select evaluacion_id, count(*) as total
      from public.preguntas_evaluacion group by evaluacion_id) n on n.evaluacion_id = e.id
where p.tipo = 'bloque'
  and exists (select 1 from public.profiles f where f.id = p.usuario_id)
  and not exists (
    select 1 from public.intentos_evaluacion i
    where i.evaluacion_id = e.id and i.estudiante_id = p.usuario_id
      and i.respuestas = '{}'::jsonb)
"""

# Solo lo que creo esta revision: evaluaciones globales sin autor con el titulo generado.
# destructivo-aprobado: HU-B-308 (downgrade de una revision de datos; borra solo lo copiado)
QUITAR_COPIA = """
delete from public.evaluaciones
where curso_id is null and autor_id is null and titulo like 'Evaluación del bloque %'
"""


def upgrade() -> None:
    op.execute(CREAR_EVALUACIONES)
    op.execute(COPIAR_PREGUNTAS)
    op.execute(COPIAR_RESULTADOS)


def downgrade() -> None:
    op.execute(QUITAR_COPIA)
