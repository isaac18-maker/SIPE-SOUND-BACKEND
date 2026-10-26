# =========================================================
# Solicitudes de inscripcion a cursos (HU-B-414). Consultas agregadas fijas (sin N+1). Nunca
# selecciona correos. No abre ni confirma transacciones: usa la sesion del servicio.
# =========================================================
from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

# Catalogo del estudiante: todos los cursos activos y su relacion con el, en una sola consulta.
CATALOGO = """
select c.id, c.nombre, c.descripcion, c.nivel,
  d.nombre as docente_nombre, d.apellido as docente_apellido,
  (select count(*) from public.inscripciones i where i.curso_id = c.id)::int as estudiantes,
  (select count(*) from public.curso_bloques cb where cb.curso_id = c.id)::int as bloques_en_ruta,
  case
    when exists (select 1 from public.inscripciones i
                 where i.curso_id = c.id and i.estudiante_id = cast(:estudiante as uuid))
      then 'inscrito'
    when exists (select 1 from public.solicitudes_inscripcion s
                 where s.curso_id = c.id and s.estudiante_id = cast(:estudiante as uuid)
                   and s.estado = 'pendiente') then 'pendiente'
    when (select s.estado from public.solicitudes_inscripcion s
          where s.curso_id = c.id and s.estudiante_id = cast(:estudiante as uuid)
          order by s.creado_en desc limit 1) = 'rechazada' then 'rechazada'
    else null
  end as mi_estado
from public.cursos c
left join public.profiles d on d.id = c.docente_id
where c.archivado_en is null
order by c.nombre, c.id
"""

# Panel: solicitudes con el nombre del estudiante y del curso. :docente nulo = todas (admin).
LISTA = """
select s.id, s.curso_id, c.nombre as curso, c.docente_id is null as curso_sin_docente,
  s.estudiante_id, e.nombre, e.apellido, s.estado, s.creado_en, s.resuelta_en,
  r.nombre as resuelta_por_nombre, r.apellido as resuelta_por_apellido
from public.solicitudes_inscripcion s
join public.cursos c on c.id = s.curso_id
join public.profiles e on e.id = s.estudiante_id
left join public.profiles r on r.id = s.resuelta_por
where (cast(:docente as uuid) is null or c.docente_id = cast(:docente as uuid))
  and (cast(:estado as text) is null or s.estado = cast(:estado as text))
  and (cast(:curso as int) is null or s.curso_id = cast(:curso as int))
order by (s.estado <> 'pendiente'), coalesce(s.resuelta_en, s.creado_en) desc, s.id
"""

# Cuantas hay de cada estado en el mismo alcance (para las pestanas, sin depender del filtro).
TOTALES = """
select s.estado, count(*)::int as total
from public.solicitudes_inscripcion s
join public.cursos c on c.id = s.curso_id
where (cast(:docente as uuid) is null or c.docente_id = cast(:docente as uuid))
group by s.estado
"""

OBTENER = """
select s.id, s.curso_id, s.estudiante_id, s.estado, c.docente_id, c.archivado_en
from public.solicitudes_inscripcion s
join public.cursos c on c.id = s.curso_id
where s.id = cast(:id as uuid)
for update of s
"""

CREAR = """
insert into public.solicitudes_inscripcion (curso_id, estudiante_id)
values (:curso, cast(:estudiante as uuid))
returning id, curso_id, estudiante_id, estado, creado_en
"""

RESOLVER = """
update public.solicitudes_inscripcion
set estado = :estado, resuelta_en = now(), resuelta_por = cast(:por as uuid)
where id = cast(:id as uuid) and estado = 'pendiente'
returning id, curso_id, estudiante_id, estado, resuelta_en
"""

CANCELAR = """
delete from public.solicitudes_inscripcion
where curso_id = :curso and estudiante_id = cast(:estudiante as uuid) and estado = 'pendiente'
returning id
"""

INSCRITO = """
select 1 from public.inscripciones
where curso_id = :curso and estudiante_id = cast(:estudiante as uuid)
"""

CURSO_ACTIVO = "select id from public.cursos where id = :curso and archivado_en is null"


class SqlSolicitudInscripcionRepository:
    def catalogo(self, sesion: Session, estudiante_id: str) -> list[Fila]:
        return filas_sql(sesion, CATALOGO, {"estudiante": estudiante_id})

    def listar(
        self, sesion: Session, docente_id: str | None, estado: str | None, curso_id: int | None
    ) -> list[Fila]:
        parametros = {"docente": docente_id, "estado": estado, "curso": curso_id}
        return filas_sql(sesion, LISTA, parametros)

    def totales(self, sesion: Session, docente_id: str | None) -> dict[str, int]:
        filas = filas_sql(sesion, TOTALES, {"docente": docente_id})
        base = {"pendiente": 0, "aceptada": 0, "rechazada": 0}
        return {**base, **{f["estado"]: f["total"] for f in filas}}

    def obtener_para_resolver(self, sesion: Session, solicitud_id: str) -> Fila | None:
        filas = filas_sql(sesion, OBTENER, {"id": solicitud_id})
        return filas[0] if filas else None

    def crear(self, sesion: Session, curso_id: int, estudiante_id: str) -> Fila:
        return filas_sql(sesion, CREAR, {"curso": curso_id, "estudiante": estudiante_id})[0]

    def resolver(self, sesion: Session, solicitud_id: str, estado: str, por: str) -> Fila | None:
        filas = filas_sql(sesion, RESOLVER, {"id": solicitud_id, "estado": estado, "por": por})
        return filas[0] if filas else None

    def cancelar(self, sesion: Session, curso_id: int, estudiante_id: str) -> bool:
        return bool(filas_sql(sesion, CANCELAR, {"curso": curso_id, "estudiante": estudiante_id}))

    def esta_inscrito(self, sesion: Session, curso_id: int, estudiante_id: str) -> bool:
        return bool(filas_sql(sesion, INSCRITO, {"curso": curso_id, "estudiante": estudiante_id}))

    def curso_activo(self, sesion: Session, curso_id: int) -> bool:
        return bool(filas_sql(sesion, CURSO_ACTIVO, {"curso": curso_id}))
