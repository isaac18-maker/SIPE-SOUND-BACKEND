# =========================================================
# Panel de progreso del docente (HU-B-408). Cada consulta agrega para TODOS los cursos y
# estudiantes del alcance a la vez (sin N+1): el numero de sentencias no crece con el
# numero de cursos ni de estudiantes. Nunca selecciona correos.
# Reutiliza las definiciones de HU-B-310: la ruta de un curso es la suya o, si no definio la
# suya, la global; avance = lecciones completadas de la ruta / lecciones de la ruta.
# =========================================================
from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

# Alcance: cursos ACTIVOS del docente (:docente nulo = todos, para el administrador),
# opcionalmente uno solo (:curso). Todo lo demas se calcula sobre ese alcance.
BASE = """
alcance as (
  select c.id, c.nombre from public.cursos c
  where c.archivado_en is null
    and (cast(:docente as uuid) is null or c.docente_id = cast(:docente as uuid))
    and (cast(:curso as int) is null or c.id = cast(:curso as int))
),
ruta_propia as (
  select cb.curso_id, cb.bloque_id, cb.orden
  from public.curso_bloques cb
  join public.bloques b on b.id = cb.bloque_id and b.estado = 'publicado'
  where cb.curso_id in (select id from alcance)
),
ruta as (
  select curso_id, bloque_id, orden from ruta_propia
  union all
  select a.id, b.id, b.orden_index
  from alcance a cross join public.bloques b
  where b.estado = 'publicado'
    and not exists (select 1 from ruta_propia rp where rp.curso_id = a.id)
),
lecciones_ruta as (
  select r.curso_id, l.id as leccion_id
  from ruta r
  join public.lecciones l on l.bloque_id = r.bloque_id and l.estado = 'publicado'
),
est as (
  select i.curso_id, i.estudiante_id, p.nombre, p.apellido,
    (select count(*) from public.progreso_lecciones pl
      where pl.estudiante_id = i.estudiante_id and pl.completado
        and pl.leccion_id in (
          select lr.leccion_id from lecciones_ruta lr where lr.curso_id = i.curso_id)
    ) as completadas,
    (select count(*) from lecciones_ruta lr where lr.curso_id = i.curso_id) as total_lecciones,
    greatest(
      (select max(actualizado_en) from public.progreso_lecciones
        where estudiante_id = i.estudiante_id),
      (select max(actualizado_en) from public.progreso_ejercicios
        where estudiante_id = i.estudiante_id),
      (select max(creado_en) from public.intentos_evaluacion
        where estudiante_id = i.estudiante_id)) as ultimo_avance
  from public.inscripciones i
  join alcance a on a.id = i.curso_id
  join public.profiles p on p.id = i.estudiante_id
),
-- Intentos en las evaluaciones GLOBALES de los bloques de la ruta (como RutaRepository.desempeno).
intentos_bloque as (
  select e.curso_id, e.estudiante_id, ev.bloque_id, it.puntaje, it.aprobado, it.respuestas,
         ev.id as evaluacion_id
  from est e
  join public.intentos_evaluacion it on it.estudiante_id = e.estudiante_id
  join public.evaluaciones ev on ev.id = it.evaluacion_id and ev.curso_id is null
  where ev.bloque_id in (select r.bloque_id from ruta r where r.curso_id = e.curso_id)
)"""

RESUMEN_CURSOS = f"""
with {BASE},
medidas as (
  select e.*,
    case when e.total_lecciones = 0 then 0
         else e.completadas * 100.0 / e.total_lecciones end as avance
  from est e
)
select a.id, a.nombre,
  count(m.estudiante_id)::int as estudiantes,
  coalesce(round(avg(m.avance)), 0)::int as avance_promedio,
  (count(*) filter (where m.ultimo_avance >= now() - interval '7 days'))::int
    as estudiantes_al_dia,
  (count(*) filter (where m.estudiante_id is not null
     and (m.ultimo_avance is null or m.ultimo_avance < now() - interval '14 days')))::int
    as sin_actividad_14_dias
from alcance a left join medidas m on m.curso_id = a.id
group by a.id, a.nombre
order by a.nombre, a.id
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

BLOQUES_POR_CURSO = f"""
with {BASE},
bloque_ruta as (
  select r.curso_id, r.bloque_id, r.orden, b.numero, b.titulo
  from ruta r join public.bloques b on b.id = r.bloque_id
),
por_estudiante as (
  select curso_id, estudiante_id, bloque_id, count(*) as intentos,
         max(puntaje) as mejor, bool_or(aprobado) as aprobo
  from intentos_bloque
  group by curso_id, estudiante_id, bloque_id
),
fallos as (
  select ib.curso_id, ib.bloque_id, p.id as pregunta_id, p.orden,
    left(p.enunciado, 120) as enunciado,
    count(*) filter (
      where (ib.respuestas -> cast(p.id as text)) is distinct from to_jsonb(p.respuesta_correcta)
    ) as fallos
  from intentos_bloque ib
  join public.preguntas_evaluacion p on p.evaluacion_id = ib.evaluacion_id
  group by ib.curso_id, ib.bloque_id, p.id, p.orden, p.enunciado
),
peor as (
  select distinct on (curso_id, bloque_id) curso_id, bloque_id, enunciado, fallos
  from fallos where fallos > 0
  order by curso_id, bloque_id, fallos desc, orden
)
select br.curso_id, br.bloque_id, br.numero, br.titulo, br.orden,
  (count(*) filter (where pe.aprobo))::int as aprobados,
  coalesce(sum(pe.intentos), 0)::int as intentos,
  round(avg(pe.mejor))::int as promedio_mejor_puntaje,
  pw.enunciado as pregunta_mas_fallada, pw.fallos::int as fallos_de_la_pregunta
from bloque_ruta br
left join por_estudiante pe on pe.curso_id = br.curso_id and pe.bloque_id = br.bloque_id
left join peor pw on pw.curso_id = br.curso_id and pw.bloque_id = br.bloque_id
group by br.curso_id, br.bloque_id, br.numero, br.titulo, br.orden, pw.enunciado, pw.fallos
order by br.curso_id, br.orden
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

NECESITAN_APOYO = f"""
with {BASE},
reprobados as (
  select curso_id, estudiante_id, bloque_id,
         (count(*) filter (where not aprobado))::int as reprobados
  from intentos_bloque
  group by curso_id, estudiante_id, bloque_id
  having not bool_or(aprobado) and count(*) filter (where not aprobado) >= 2
),
peor_bloque as (
  select distinct on (curso_id, estudiante_id) curso_id, estudiante_id, bloque_id, reprobados
  from reprobados
  order by curso_id, estudiante_id, reprobados desc, bloque_id
),
candidatos as (
  select e.curso_id, a.nombre as curso, e.estudiante_id, e.nombre, e.apellido, e.ultimo_avance,
    (e.ultimo_avance is null or e.ultimo_avance < now() - interval '14 days') as sin_actividad,
    pb.bloque_id as bloque_reprobado_id, b.titulo as bloque_reprobado,
    pb.reprobados as intentos_reprobados
  from est e
  join alcance a on a.id = e.curso_id
  left join peor_bloque pb on pb.curso_id = e.curso_id and pb.estudiante_id = e.estudiante_id
  left join public.bloques b on b.id = pb.bloque_id
)
select * from candidatos
where sin_actividad or bloque_reprobado_id is not null
order by (bloque_reprobado_id is not null) desc, ultimo_avance asc nulls first, nombre,
         estudiante_id
limit :limite
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

CELDAS = """
select it.estudiante_id, ev.bloque_id,
  count(*)::int as intentos, max(it.puntaje)::int as mejor_puntaje,
  bool_or(it.aprobado) as aprobado
from public.intentos_evaluacion it
join public.evaluaciones ev on ev.id = it.evaluacion_id and ev.curso_id is null
where it.estudiante_id = any(cast(:estudiantes as uuid[]))
  and ev.bloque_id = any(cast(:bloques as int[]))
group by it.estudiante_id, ev.bloque_id
"""

CURSOS_DEL_ESTUDIANTE = """
select i.curso_id
from public.inscripciones i join public.cursos c on c.id = i.curso_id
where i.estudiante_id = cast(:estudiante as uuid)
  and c.archivado_en is null
  and (cast(:docente as uuid) is null or c.docente_id = cast(:docente as uuid))
order by c.nombre, c.id
"""


class SqlProgresoDocenteRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def resumen_cursos(
        self, sesion: Session, docente_id: str | None, curso_id: int | None
    ) -> list[Fila]:
        return filas_sql(sesion, RESUMEN_CURSOS, {"docente": docente_id, "curso": curso_id})

    def bloques_por_curso(
        self, sesion: Session, docente_id: str | None, curso_id: int | None
    ) -> list[Fila]:
        return filas_sql(sesion, BLOQUES_POR_CURSO, {"docente": docente_id, "curso": curso_id})

    def necesitan_apoyo(
        self, sesion: Session, docente_id: str | None, curso_id: int | None, limite: int
    ) -> list[Fila]:
        parametros = {"docente": docente_id, "curso": curso_id, "limite": limite}
        return filas_sql(sesion, NECESITAN_APOYO, parametros)

    def celdas(
        self, sesion: Session, estudiante_ids: list[str], bloque_ids: list[int]
    ) -> list[Fila]:
        parametros = {"estudiantes": estudiante_ids, "bloques": bloque_ids}
        return filas_sql(sesion, CELDAS, parametros)

    def cursos_del_estudiante(
        self, sesion: Session, docente_id: str | None, estudiante_id: str
    ) -> list[int]:
        parametros = {"docente": docente_id, "estudiante": estudiante_id}
        return [f["curso_id"] for f in filas_sql(sesion, CURSOS_DEL_ESTUDIANTE, parametros)]
