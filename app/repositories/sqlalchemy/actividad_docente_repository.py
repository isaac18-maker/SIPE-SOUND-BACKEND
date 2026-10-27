# =========================================================
# Actividad del docente (HU-B-418). Cada consulta del admin es UNA sentencia SQL con subconsultas
# agregadas (sin N+1). Solo agregados: nunca correos ni apellidos de estudiantes, ni el contenido
# de lo que hizo el docente. Usa la sesion del servicio.
# El avance de los estudiantes usa la misma definicion que el panel del docente (HU-B-408/310):
# lecciones publicadas de la ruta del curso (o la global si no definio la suya) completadas.
# =========================================================
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVIDAD_ACTIVO,
    ACTIVIDAD_ACTIVO_DIAS,
    ACTIVIDAD_INACTIVO,
    ACTIVIDAD_INACTIVO_DIAS,
    ACTIVIDAD_SIN_ACTIVIDAD,
    ZONA_HORARIA,
)
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql
from app.repositories.sqlalchemy.admin_cuentas_repository import ESTADO_SQL, _escapar_like

ULTIMA_ACTIVIDAD_SQL = (
    "(select max(a.creado_en) from public.actividad_docente a where a.docente_id = p.id)"
)


def estado_actividad_sql(ultima: str) -> str:
    """activo (<= 7 dias), inactivo (8 a 30) o sin_actividad (mas de 30 o nunca)."""
    return f"""case
      when {ultima} is null
        or {ultima} < now() - interval '{ACTIVIDAD_INACTIVO_DIAS} days'
        then '{ACTIVIDAD_SIN_ACTIVIDAD}'
      when {ultima} >= now() - interval '{ACTIVIDAD_ACTIVO_DIAS} days' then '{ACTIVIDAD_ACTIVO}'
      else '{ACTIVIDAD_INACTIVO}' end"""


ESTUDIANTES_ACTIVOS = """(select count(distinct i.estudiante_id) from public.inscripciones i
       join public.cursos c on c.id = i.curso_id
      where c.docente_id = p.id and c.archivado_en is null)"""

LISTADO = f"""
with base as (
  select p.id as docente_id,
    concat_ws(' ', p.nombre, p.apellido) as nombre,
    u.email,
    {ULTIMA_ACTIVIDAD_SQL} as ultima_actividad,
    (select count(*) from public.actividad_docente a
      where a.docente_id = p.id and a.creado_en >= now() - interval '30 days') as acciones_30d,
    (select count(*) from public.cursos c
      where c.docente_id = p.id and c.archivado_en is null) as cursos_asignados,
    {ESTUDIANTES_ACTIVOS} as estudiantes
  from public.profiles p join auth.users u on u.id = p.id
  where p.rol = 'docente' and {ESTADO_SQL} = 'activa'
    and (cast(:q as text) is null or p.nombre ilike :patron or p.apellido ilike :patron
         or u.email ilike :patron)
), con_estado as (
  select base.*, {estado_actividad_sql("base.ultima_actividad")} as estado_actividad from base
)
select con_estado.*, count(*) over () as total_filas
from con_estado
where (cast(:estado as text) is null or estado_actividad = :estado)
order by {{orden}}
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

# El ORDER BY sale de un diccionario cerrado; el valor del usuario nunca se concatena.
ORDENES = {
    "ultima_actividad": "ultima_actividad asc nulls first, nombre, docente_id",
    "-acciones_30d": "acciones_30d desc, nombre, docente_id",
    "-cursos": "cursos_asignados desc, nombre, docente_id",
    "-estudiantes": "estudiantes desc, nombre, docente_id",
    "nombre": "nombre asc, docente_id",
}

ES_DOCENTE = "select 1 as ok from public.profiles where id = cast(:id as uuid) and rol = 'docente'"

DESDE = (
    "((now() at time zone :zona)::date - (cast(:dias as int) - 1))::timestamp at time zone :zona"
)

POR_DIA = f"""
with hoy as (select (now() at time zone :zona)::date as d),
n as (
  select (creado_en at time zone :zona)::date as dia, count(*) as acciones
  from public.actividad_docente
  where docente_id = cast(:id as uuid) and creado_en >= {DESDE}
  group by 1
)
select to_char(hoy.d - (cast(:dias as int) - 1 - g), 'YYYY-MM-DD') as fecha,
  coalesce(n.acciones, 0) as acciones
from hoy cross join generate_series(0, cast(:dias as int) - 1) as g
left join n on n.dia = hoy.d - (cast(:dias as int) - 1 - g)
order by g
"""  # noqa: S608 - solo fragmentos constantes

POR_TIPO = f"""
select tipo, count(*) as acciones
from public.actividad_docente
where docente_id = cast(:id as uuid) and creado_en >= {DESDE}
group by tipo
order by acciones desc, tipo
"""  # noqa: S608

ULTIMA_DEL_DOCENTE = (
    "(select max(creado_en) from public.actividad_docente where docente_id = cast(:id as uuid))"
)

TOTALES = f"""
select
  (select count(distinct (creado_en at time zone :zona)::date)
     from public.actividad_docente
    where docente_id = cast(:id as uuid) and creado_en >= {DESDE}) as dias_activos,
  {ULTIMA_DEL_DOCENTE} as ultima_actividad,
  {estado_actividad_sql(ULTIMA_DEL_DOCENTE)} as estado_actividad
"""  # noqa: S608

CURSOS_ASIGNADOS = """
with cursos_d as (
  select c.id, c.nombre from public.cursos c
  where c.docente_id = cast(:id as uuid) and c.archivado_en is null
),
ruta as (
  select cb.curso_id, cb.bloque_id from public.curso_bloques cb
  join public.bloques b on b.id = cb.bloque_id and b.estado = 'publicado'
  where cb.curso_id in (select id from cursos_d)
  union all
  select c.id, b.id from cursos_d c cross join public.bloques b
  where b.estado = 'publicado'
    and not exists (select 1 from public.curso_bloques cb where cb.curso_id = c.id)
),
lecc as (
  select r.curso_id, l.id as leccion_id from ruta r
  join public.lecciones l on l.bloque_id = r.bloque_id and l.estado = 'publicado'
),
total as (select curso_id, count(*) as n from lecc group by curso_id),
est as (
  select i.curso_id, i.estudiante_id,
    (select count(*) from public.progreso_lecciones pl
      where pl.estudiante_id = i.estudiante_id and pl.completado
        and pl.leccion_id in (select leccion_id from lecc where lecc.curso_id = i.curso_id))
      as completadas,
    greatest(
      (select max(actualizado_en) from public.progreso_lecciones
        where estudiante_id = i.estudiante_id),
      (select max(actualizado_en) from public.progreso_ejercicios
        where estudiante_id = i.estudiante_id),
      (select max(creado_en) from public.intentos_evaluacion
        where estudiante_id = i.estudiante_id)) as ultimo_avance
  from public.inscripciones i
  where i.curso_id in (select id from cursos_d)
)
select c.id as curso_id, c.nombre,
  count(e.estudiante_id) as estudiantes,
  coalesce(round(avg(case when coalesce(t.n, 0) = 0 then 0
                          else e.completadas * 100.0 / t.n end)), 0) as avance_promedio_pct,
  count(e.estudiante_id) filter (
    where e.ultimo_avance is null or e.ultimo_avance < now() - interval '7 days'
  ) as estudiantes_sin_actividad_7d,
  (select max(a.creado_en) from public.actividad_docente a
    where a.curso_id = c.id and a.docente_id = cast(:id as uuid)) as ultima_actividad_docente
from cursos_d c
left join est e on e.curso_id = c.id
left join total t on t.curso_id = c.id
group by c.id, c.nombre, t.n
order by c.nombre, c.id
"""

# La línea de tiempo filtra por un tipo o por un grupo: "contenido" (lecciones, ejercicios y
# cursos) y "evaluacion" (evaluaciones y retroalimentaciones).
GRUPOS_DE_TIPO = {
    "contenido": ["leccion", "ejercicio", "curso"],
    "evaluacion": ["evaluacion", "retroalimentacion"],
}

LINEA_DE_TIEMPO = """
select a.creado_en, a.tipo, a.accion, a.curso_id, c.nombre as curso_nombre,
  count(*) over () as total_filas
from public.actividad_docente a left join public.cursos c on c.id = a.curso_id
where a.docente_id = cast(:id as uuid)
  and (cast(:tipos as text[]) is null or a.tipo = any(cast(:tipos as text[])))
  and (cast(:curso_id as int) is null or a.curso_id = :curso_id)
  and (cast(:desde as date) is null or (a.creado_en at time zone :zona)::date >= :desde)
  and (cast(:hasta as date) is null or (a.creado_en at time zone :zona)::date <= :hasta)
order by a.creado_en desc, a.id
limit :limite offset :offset
"""

REGISTRAR = text(
    "insert into public.actividad_docente (docente_id, curso_id, tipo, accion) "
    "values (cast(:docente_id as uuid), :curso_id, :tipo, :accion)"
)
# Un inicio de sesion como maximo cada :minutos, y solo si la cuenta es de un docente.
REGISTRAR_INICIO = text(
    "insert into public.actividad_docente (docente_id, tipo, accion) "
    "select p.id, 'sesion', 'inicio' from public.profiles p "
    "where p.id = cast(:id as uuid) and p.rol = 'docente' "
    "and not exists (select 1 from public.actividad_docente a where a.docente_id = p.id "
    "and a.tipo = 'sesion' and a.creado_en > now() - make_interval(mins => :minutos))"
)
LIMPIAR = text(
    "delete from public.actividad_docente where id in ("
    "select id from public.actividad_docente "
    "where creado_en < now() - make_interval(days => :dias) limit :lote)"
)


class SqlActividadDocenteRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def registrar(
        self, sesion: Session, docente_id: str, curso_id: int | None, tipo: str, accion: str
    ) -> None:
        sesion.execute(
            REGISTRAR,
            {"docente_id": docente_id, "curso_id": curso_id, "tipo": tipo, "accion": accion},
        )

    def registrar_inicio(self, sesion: Session, docente_id: str, *, cada_minutos: int) -> bool:
        resultado = sesion.execute(REGISTRAR_INICIO, {"id": docente_id, "minutos": cada_minutos})
        return resultado.rowcount > 0

    def limpiar(self, sesion: Session, *, dias: int, lote: int) -> int:
        return sesion.execute(LIMPIAR, {"dias": dias, "lote": lote}).rowcount

    def es_docente(self, sesion: Session, docente_id: str) -> bool:
        return bool(filas_sql(sesion, ES_DOCENTE, {"id": docente_id}))

    def listar(  # noqa: PLR0913
        self,
        sesion: Session,
        *,
        q: str | None,
        estado_actividad: str | None,
        orden: str,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            LISTADO.format(orden=ORDENES[orden]),
            {
                "q": q,
                "patron": f"%{_escapar_like(q)}%" if q else None,
                "estado": estado_actividad,
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        total = filas[0]["total_filas"] if filas else 0
        for fila in filas:
            fila.pop("total_filas")
        return filas, total

    def resumen(self, sesion: Session, docente_id: str, dias: int) -> Fila:
        parametros: dict[str, Any] = {"id": docente_id, "dias": dias, "zona": ZONA_HORARIA}
        totales = filas_sql(sesion, TOTALES, parametros)[0]
        return {
            "por_dia": filas_sql(sesion, POR_DIA, parametros),
            "por_tipo": filas_sql(sesion, POR_TIPO, parametros),
            "dias_activos": int(totales["dias_activos"]),
            "ultima_actividad": totales["ultima_actividad"],
            "estado_actividad": totales["estado_actividad"],
            "cursos": [
                {**c, "avance_promedio_pct": int(c["avance_promedio_pct"])}
                for c in filas_sql(sesion, CURSOS_ASIGNADOS, {"id": docente_id})
            ],
        }

    def linea_de_tiempo(  # noqa: PLR0913
        self,
        sesion: Session,
        docente_id: str,
        *,
        tipo: str | None,
        curso_id: int | None,
        desde: date | None,
        hasta: date | None,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            LINEA_DE_TIEMPO,
            {
                "id": docente_id,
                "tipos": GRUPOS_DE_TIPO.get(tipo, [tipo]) if tipo else None,
                "curso_id": curso_id,
                "desde": desde,
                "hasta": hasta,
                "zona": ZONA_HORARIA,
                "limite": por_pagina,
                "offset": (pagina - 1) * por_pagina,
            },
        )
        total = filas[0]["total_filas"] if filas else 0
        for fila in filas:
            fila.pop("total_filas")
        return filas, total
