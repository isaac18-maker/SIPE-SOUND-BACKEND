# =========================================================
# Panel de progreso del docente (HU-B-408). Cada consulta agrega para TODOS los cursos y
# estudiantes del alcance a la vez (sin N+1): el numero de sentencias no crece con el
# numero de cursos ni de estudiantes. Nunca selecciona correos.
# Reutiliza las definiciones de HU-B-310: la ruta de un curso es la suya o, si no definio la
# suya, la global; avance = lecciones completadas de la ruta / lecciones de la ruta.
# =========================================================
from sqlalchemy.orm import Session

from app.core.constants import ZONA_HORARIA
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
ruta_completa as (
  select curso_id, bloque_id, orden from ruta_propia
  union all
  select a.id, b.id, b.orden_index
  from alcance a cross join public.bloques b
  where b.estado = 'publicado'
    and not exists (select 1 from ruta_propia rp where rp.curso_id = a.id)
),
-- :bloque nulo = toda la ruta. Se filtra DESPUES de resolver la ruta: un curso con ruta propia
-- que no incluye ese bloque no debe caer en la ruta global.
ruta as (
  select * from ruta_completa
  where cast(:bloque as int) is null or bloque_id = cast(:bloque as int)
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
         ev.id as evaluacion_id, it.id as intento_id, it.creado_en as intento_en
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

# ---- Series para las graficas (HU-B-503) -------------------------------------------------
# `sel` = inscripciones del alcance que pasan el filtro de estudiantes. Todas las series parten de
# el, asi que coinciden entre si y con la matriz (mismo alcance, misma ruta, mismas definiciones).
SELECCION = """
reprobados as (
  select curso_id, estudiante_id, bloque_id
  from intentos_bloque
  group by curso_id, estudiante_id, bloque_id
  having not bool_or(aprobado) and count(*) filter (where not aprobado) >= 2
),
con_evaluacion as (
  select r.curso_id, r.bloque_id, ev.id as evaluacion_id
  from ruta r
  join public.evaluaciones ev on ev.bloque_id = r.bloque_id and ev.curso_id is null
    and ev.estado = 'publicada'
),
medidas as (
  select e.curso_id, e.estudiante_id,
    case when e.total_lecciones = 0 then 0
         else least(100, round(e.completadas * 100.0 / e.total_lecciones)::int) end as avance_pct,
    -- hay registro: algun avance de leccion o ejercicio de la ruta, o algun intento
    (exists (select 1 from public.progreso_lecciones pl
              where pl.estudiante_id = e.estudiante_id
                and pl.leccion_id in (select lr.leccion_id from lecciones_ruta lr
                                       where lr.curso_id = e.curso_id))
     or exists (select 1 from public.progreso_ejercicios pe
                 join public.ejercicios x on x.id = pe.ejercicio_id
                 where pe.estudiante_id = e.estudiante_id
                   and x.leccion_id in (select lr.leccion_id from lecciones_ruta lr
                                         where lr.curso_id = e.curso_id))
     or exists (select 1 from intentos_bloque ib
                 where ib.curso_id = e.curso_id and ib.estudiante_id = e.estudiante_id)
    ) as hay_registro,
    -- finalizado: lecciones de la ruta completas y evaluaciones de sus bloques aprobadas
    -- (misma regla que app/core/avance.curso_completo)
    (e.total_lecciones > 0 and e.completadas >= e.total_lecciones
     and not exists (
       select 1 from con_evaluacion ce
       where ce.curso_id = e.curso_id
         and not exists (select 1 from public.intentos_evaluacion it
                          where it.evaluacion_id = ce.evaluacion_id
                            and it.estudiante_id = e.estudiante_id and it.aprobado))
    ) as completo,
    (e.ultimo_avance >= now() - interval '7 days') as al_dia,
    (e.ultimo_avance is null or e.ultimo_avance < now() - interval '14 days') as sin_actividad,
    exists (select 1 from reprobados rp
             where rp.curso_id = e.curso_id and rp.estudiante_id = e.estudiante_id) as reprobo
  from est e
),
sel as (
  select * from medidas m
  where cast(:estudiantes as text) is null
     or (cast(:estudiantes as text) = 'al_dia' and m.al_dia)
     or (cast(:estudiantes as text) = 'sin_actividad' and m.sin_actividad)
     or (cast(:estudiantes as text) = 'en_riesgo' and (m.sin_actividad or m.reprobo))
)"""

AVANCE_DE_LA_SELECCION = f"""
with {BASE},
{SELECCION}
select least(avance_pct / 20, 4)::int as tramo, hay_registro, completo, count(*)::int as estudiantes
from sel
group by 1, 2, 3
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

ACTIVIDAD_DE_LA_SELECCION = f"""
with {BASE},
{SELECCION},
-- Un evento por registro de avance. UNION (no ALL): si un estudiante esta en dos cursos que
-- comparten la leccion, el registro se cuenta una sola vez.
eventos as (
  select s.estudiante_id, 'l' || pl.leccion_id as ref, pl.actualizado_en as fecha
  from sel s
  join lecciones_ruta lr on lr.curso_id = s.curso_id
  join public.progreso_lecciones pl
    on pl.leccion_id = lr.leccion_id and pl.estudiante_id = s.estudiante_id
  union
  select s.estudiante_id, 'e' || pe.ejercicio_id, pe.actualizado_en
  from sel s
  join lecciones_ruta lr on lr.curso_id = s.curso_id
  join public.ejercicios x on x.leccion_id = lr.leccion_id
  join public.progreso_ejercicios pe
    on pe.ejercicio_id = x.id and pe.estudiante_id = s.estudiante_id
  union
  select s.estudiante_id, 'i' || ib.intento_id, ib.intento_en
  from sel s
  join intentos_bloque ib
    on ib.curso_id = s.curso_id and ib.estudiante_id = s.estudiante_id
),
hoy as (select (now() at time zone :zona)::date as dia)
select d::date as fecha,
  count(distinct e.estudiante_id)::int as estudiantes_activos,
  count(e.ref)::int as registros
from hoy, generate_series(hoy.dia - (:dias - 1), hoy.dia, interval '1 day') as d
left join eventos e on (e.fecha at time zone :zona)::date = d::date
group by d order by d
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

EVALUACIONES_DE_LA_SELECCION = f"""
with {BASE},
{SELECCION},
-- Las globales de los bloques de la ruta y las propias de los cursos del alcance. Se listan
-- tambien en borrador y cerradas: el docente decide desde aqui cuales abrir o cerrar.
de_alcance as (
  select ev.id, ev.titulo, ev.estado, ev.bloque_id, ev.curso_id
  from public.evaluaciones ev
  where (ev.curso_id in (select id from alcance)
         or (ev.curso_id is null and ev.bloque_id in (select bloque_id from ruta)))
    and (cast(:bloque as int) is null or ev.bloque_id = cast(:bloque as int))
),
destinatarios as (
  select ev.id as evaluacion_id, s.estudiante_id
  from de_alcance ev
  join sel s on ev.curso_id = s.curso_id
    or (ev.curso_id is null and exists (
         select 1 from ruta r where r.curso_id = s.curso_id and r.bloque_id = ev.bloque_id))
  group by ev.id, s.estudiante_id
)
select ev.id as evaluacion_id, ev.titulo, ev.estado, ev.bloque_id, ev.curso_id,
  count(it.id)::int as intentos,
  (count(distinct it.estudiante_id) filter (where it.aprobado))::int as aprobados,
  round(avg(it.puntaje))::int as promedio_puntaje
from de_alcance ev
left join destinatarios d on d.evaluacion_id = ev.id
left join public.intentos_evaluacion it
  on it.evaluacion_id = ev.id and it.estudiante_id = d.estudiante_id
group by ev.id, ev.titulo, ev.estado, ev.bloque_id, ev.curso_id
order by ev.bloque_id nulls last, ev.id
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
        return filas_sql(
            sesion, RESUMEN_CURSOS, {"docente": docente_id, "curso": curso_id, "bloque": None}
        )

    def bloques_por_curso(
        self, sesion: Session, docente_id: str | None, curso_id: int | None
    ) -> list[Fila]:
        return filas_sql(
            sesion, BLOQUES_POR_CURSO, {"docente": docente_id, "curso": curso_id, "bloque": None}
        )

    def necesitan_apoyo(
        self, sesion: Session, docente_id: str | None, curso_id: int | None, limite: int
    ) -> list[Fila]:
        parametros = {"docente": docente_id, "curso": curso_id, "bloque": None, "limite": limite}
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

    def avance_de_la_seleccion(self, sesion: Session, filtros: Fila) -> list[Fila]:
        """Inscripciones agrupadas por (tramo de 20 %, hay registro, completo). El estado se
        deriva fuera, con app/core/avance, para que sea el mismo que ve el estudiante."""
        return filas_sql(sesion, AVANCE_DE_LA_SELECCION, self._parametros(filtros))

    def actividad_por_dia(self, sesion: Session, filtros: Fila, dias: int) -> list[Fila]:
        parametros = {**self._parametros(filtros), "dias": dias, "zona": ZONA_HORARIA}
        return filas_sql(sesion, ACTIVIDAD_DE_LA_SELECCION, parametros)

    def evaluaciones(self, sesion: Session, filtros: Fila) -> list[Fila]:
        return filas_sql(sesion, EVALUACIONES_DE_LA_SELECCION, self._parametros(filtros))

    @staticmethod
    def _parametros(filtros: Fila) -> Fila:
        return {
            "docente": filtros["docente_id"],
            "curso": filtros["curso_id"],
            "bloque": filtros["bloque_id"],
            "estudiantes": filtros["estudiantes"],
        }
