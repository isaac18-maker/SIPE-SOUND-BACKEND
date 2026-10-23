# =========================================================
# Seguimiento del docente (HU-B-310): avance de los estudiantes de un curso,
# detalle de un estudiante y resumen del panel. Cada listado es UNA sentencia
# SQL con subconsultas agregadas (sin N+1). Usa la sesion del servicio.
# Lee auth.users solo para el correo (el servicio lo enmascara).
# =========================================================
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import formatear_fecha

# Bloques de la ruta del curso (o la global si el curso no definio la suya).
CTE_RUTA = """
ruta as (
  select cb.bloque_id from public.curso_bloques cb
  join public.bloques b on b.id = cb.bloque_id and b.estado = 'publicado'
  where cb.curso_id = :curso_id
  union all
  select b.id from public.bloques b
  where b.estado = 'publicado'
    and not exists (select 1 from public.curso_bloques cb where cb.curso_id = :curso_id)
),
lecciones_ruta as (
  select l.id from public.lecciones l
  where l.estado = 'publicado' and l.bloque_id in (select bloque_id from ruta)
)"""

ESTUDIANTES = f"""
with {CTE_RUTA},
total as (select count(*) as n from lecciones_ruta),
base as (
  select i.estudiante_id, i.inscrito_en, p.nombre, u.email,
    (select count(*) from public.progreso_lecciones pl
      where pl.estudiante_id = i.estudiante_id and pl.completado
        and pl.leccion_id in (select id from lecciones_ruta)) as completadas,
    (select count(distinct e.bloque_id) from public.intentos_evaluacion it
      join public.evaluaciones e on e.id = it.evaluacion_id
      where it.estudiante_id = i.estudiante_id and it.aprobado and e.curso_id is null
        and e.bloque_id in (select bloque_id from ruta)) as bloques_aprobados,
    greatest(
      (select max(actualizado_en) from public.progreso_lecciones
        where estudiante_id = i.estudiante_id),
      (select max(actualizado_en) from public.progreso_ejercicios
        where estudiante_id = i.estudiante_id),
      (select max(creado_en) from public.intentos_evaluacion
        where estudiante_id = i.estudiante_id)) as ultimo_avance
  from public.inscripciones i
  join public.profiles p on p.id = i.estudiante_id
  join auth.users u on u.id = i.estudiante_id
  where i.curso_id = :curso_id
    and (cast(:q as text) is null or p.nombre ilike :patron or u.email ilike :patron)
)
select base.*,
  case when total.n = 0 then 0 else round(base.completadas * 100.0 / total.n) end as avance_pct,
  count(*) over () as total_filas
from base, total
order by {{orden}}
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

ORDENES = {
    "nombre": "base.nombre asc, base.estudiante_id",
    "-avance_pct": "avance_pct desc, base.nombre asc",
    "-ultimo_avance": "base.ultimo_avance desc nulls last, base.nombre asc",
}


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filas(sesion: Session, sql: str, parametros: dict[str, Any]) -> list[Fila]:
    return [
        {k: formatear_fecha(v) if hasattr(v, "isoformat") else v for k, v in f._mapping.items()}
        for f in sesion.execute(text(sql), parametros)
    ]


class SqlSeguimientoRepository:
    def estudiantes(
        self,
        sesion: Session,
        curso_id: int,
        *,
        q: str | None,
        orden: str,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        # El ORDER BY sale de un diccionario cerrado; los valores del usuario van como parametros.
        sql = ESTUDIANTES.format(orden=ORDENES[orden])
        filas = _filas(
            sesion,
            sql,
            {
                "curso_id": curso_id,
                "q": q,
                "patron": f"%{_escapar_like(q)}%" if q else None,
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        total = filas[0]["total_filas"] if filas else 0
        for fila in filas:
            fila.pop("total_filas")
            fila["avance_pct"] = int(fila["avance_pct"])
        return filas, total

    def inscripcion(self, sesion: Session, curso_id: int, estudiante_id: str) -> Fila | None:
        sql = """
            select i.estudiante_id, i.inscrito_en, p.nombre, u.email
            from public.inscripciones i
            join public.profiles p on p.id = i.estudiante_id
            join auth.users u on u.id = i.estudiante_id
            where i.curso_id = :curso_id and i.estudiante_id = cast(:estudiante_id as uuid)
        """
        filas = _filas(sesion, sql, {"curso_id": curso_id, "estudiante_id": estudiante_id})
        return filas[0] if filas else None

    def ejercicios_de_lecciones(
        self, sesion: Session, leccion_ids: list[int], estudiante_id: str
    ) -> list[Fila]:
        sql = """
            select e.id, e.leccion_id, e.nombre, e.bpm_recomendado,
                   coalesce(pe.completado, false) as completado, pe.mejor_bpm
            from public.ejercicios e
            left join public.progreso_ejercicios pe
              on pe.ejercicio_id = e.id and pe.estudiante_id = cast(:estudiante_id as uuid)
            where e.estado = 'publicado' and e.leccion_id = any(:leccion_ids)
            order by e.id
        """
        return _filas(sesion, sql, {"leccion_ids": leccion_ids, "estudiante_id": estudiante_id})

    def intentos_del_estudiante(
        self, sesion: Session, curso_id: int, estudiante_id: str
    ) -> list[Fila]:
        """Intentos en evaluaciones globales y en las de ESTE curso (no de otros)."""
        sql = """
            select it.id, it.evaluacion_id, e.titulo as evaluacion, e.bloque_id,
                   it.puntaje, it.aprobado, it.creado_en
            from public.intentos_evaluacion it
            join public.evaluaciones e on e.id = it.evaluacion_id
            where it.estudiante_id = cast(:estudiante_id as uuid)
              and (e.curso_id is null or e.curso_id = :curso_id)
            order by it.creado_en desc
        """
        return _filas(sesion, sql, {"curso_id": curso_id, "estudiante_id": estudiante_id})

    def retroalimentaciones(self, sesion: Session, curso_id: int, estudiante_id: str) -> list[Fila]:
        sql = """
            select r.id, r.mensaje, r.leida_en, r.creado_en, p.nombre as docente
            from public.retroalimentaciones r
            left join public.profiles p on p.id = r.docente_id
            where r.curso_id = :curso_id and r.estudiante_id = cast(:estudiante_id as uuid)
            order by r.creado_en desc
        """
        return _filas(sesion, sql, {"curso_id": curso_id, "estudiante_id": estudiante_id})

    def resumen(self, sesion: Session, docente_id: str | None) -> Fila:
        """docente_id None = administrador (todos los cursos)."""
        parametros = {"docente_id": docente_id}
        mis_cursos = """
            select id, nombre from public.cursos
            where archivado_en is null
              and (cast(:docente_id as uuid) is null or docente_id = cast(:docente_id as uuid))
        """
        cifras = f"""
            with mis_cursos as ({mis_cursos}),
            mis_estudiantes as (
              select distinct estudiante_id from public.inscripciones
              where curso_id in (select id from mis_cursos))
            select
              (select count(*) from mis_cursos) as cursos_activos,
              (select count(*) from mis_estudiantes) as estudiantes,
              (select count(*) from public.evaluaciones
                where estado = 'publicada' and curso_id in (select id from mis_cursos))
                as evaluaciones_publicadas,
              (select count(*) from public.intentos_evaluacion
                where estudiante_id in (select estudiante_id from mis_estudiantes)
                  and creado_en >= now() - interval '7 days') as intentos_ultimos_7_dias
        """  # noqa: S608 - solo fragmentos constantes; los datos van como parametros
        sin_actividad = f"""
            with mis_cursos as ({mis_cursos}),
            actividad as (
              select i.estudiante_id, p.nombre, c.id as curso_id, c.nombre as curso,
                greatest(
                  (select max(actualizado_en) from public.progreso_lecciones
                    where estudiante_id = i.estudiante_id),
                  (select max(actualizado_en) from public.progreso_ejercicios
                    where estudiante_id = i.estudiante_id),
                  (select max(creado_en) from public.intentos_evaluacion
                    where estudiante_id = i.estudiante_id)) as ultimo_avance
              from public.inscripciones i
              join mis_cursos c on c.id = i.curso_id
              join public.profiles p on p.id = i.estudiante_id)
            select * from actividad
            where ultimo_avance is null or ultimo_avance < now() - interval '14 days'
            order by ultimo_avance asc nulls first, nombre
            limit 10
        """  # noqa: S608 - solo fragmentos constantes; los datos van como parametros
        recientes = f"""
            with mis_cursos as ({mis_cursos})
            select p.nombre as estudiante, e.titulo as evaluacion, it.puntaje, it.creado_en
            from public.intentos_evaluacion it
            join public.evaluaciones e on e.id = it.evaluacion_id
            join public.profiles p on p.id = it.estudiante_id
            where it.estudiante_id in (
              select estudiante_id from public.inscripciones
              where curso_id in (select id from mis_cursos))
              and (e.curso_id is null or e.curso_id in (select id from mis_cursos))
            order by it.creado_en desc
            limit 10
        """  # noqa: S608 - solo fragmentos constantes; los datos van como parametros
        return {
            **_filas(sesion, cifras, parametros)[0],
            "sin_actividad_14_dias": _filas(sesion, sin_actividad, parametros),
            "actividad_reciente": _filas(sesion, recientes, parametros),
        }
