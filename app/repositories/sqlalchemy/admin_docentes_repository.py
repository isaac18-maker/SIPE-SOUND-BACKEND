from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql
from app.repositories.sqlalchemy.actividad_docente_repository import (
    ULTIMA_ACTIVIDAD_SQL,
    estado_actividad_sql,
)
from app.repositories.sqlalchemy.admin_cuentas_repository import ESTADO_SQL, _escapar_like

# Conteos de un curso; se repiten en varias consultas.
ESTUDIANTES_DEL_CURSO = "(select count(*) from public.inscripciones i where i.curso_id = c.id)"
BLOQUES_DEL_CURSO = "(select count(*) from public.curso_bloques cb where cb.curso_id = c.id)"

# Una sola sentencia por pagina (count(*) over () da el total), como SqlSeguimientoRepository.
DOCENTES = f"""
with base as (
  select p.id, p.nombre, p.apellido, u.email,
    {ESTADO_SQL} as estado,
    u.last_sign_in_at as ultimo_acceso,
    {ULTIMA_ACTIVIDAD_SQL} as ultima_actividad,
    {estado_actividad_sql(ULTIMA_ACTIVIDAD_SQL)} as estado_actividad,
    (select count(*) from public.cursos c
      where c.docente_id = p.id and c.archivado_en is null) as cursos_activos,
    (select count(*) from public.cursos c
      where c.docente_id = p.id and c.archivado_en is not null) as cursos_archivados,
    (select count(distinct i.estudiante_id) from public.inscripciones i
       join public.cursos c on c.id = i.curso_id
      where c.docente_id = p.id and c.archivado_en is null) as estudiantes
  from public.profiles p join auth.users u on u.id = p.id
  where p.rol = 'docente'
    and (cast(:q as text) is null or p.nombre ilike :patron or p.apellido ilike :patron
         or u.email ilike :patron)
)
select base.*, count(*) over () as total_filas
from base
order by base.nombre asc, base.apellido asc nulls last, base.id
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

CURSOS_DE_DOCENTE = f"""
select c.id, c.nombre, c.descripcion, c.nivel, c.codigo_invitacion, c.creado_en,
  c.archivado_en, {ESTUDIANTES_DEL_CURSO} as estudiantes,
  {BLOQUES_DEL_CURSO} as bloques_en_ruta
from public.cursos c
where c.docente_id = cast(:id as uuid)
order by (c.archivado_en is not null), c.nombre, c.id
"""  # noqa: S608 - solo fragmentos constantes

CURSOS = f"""
with base as (
  select c.id, c.nombre, c.nivel, c.codigo_invitacion, c.creado_en, c.archivado_en,
    c.docente_id, d.nombre as docente, d.apellido as docente_apellido,
    case when c.archivado_en is null then 'activo' else 'archivado' end as estado,
    {ESTUDIANTES_DEL_CURSO} as estudiantes, {BLOQUES_DEL_CURSO} as bloques_en_ruta
  from public.cursos c left join public.profiles d on d.id = c.docente_id
  where (cast(:docente as uuid) is null or c.docente_id = cast(:docente as uuid))
    and (not :sin_docente or c.docente_id is null)
    and (cast(:q as text) is null or c.nombre ilike :patron or d.nombre ilike :patron
         or d.apellido ilike :patron or c.codigo_invitacion ilike :patron)
)
select base.*, count(*) over () as total_filas
from base
where (cast(:estado as text) is null or base.estado = :estado)
order by base.estado, base.nombre, base.id
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros


def _patron(q: str | None) -> str | None:
    return f"%{_escapar_like(q)}%" if q else None


def _con_total(filas: list[Fila]) -> tuple[list[Fila], int]:
    total = filas[0]["total_filas"] if filas else 0
    for fila in filas:
        fila.pop("total_filas")
    return filas, total


class SqlAdminDocentesRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def listar_docentes(
        self, sesion: Session, *, q: str | None, pagina: int, por_pagina: int
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            DOCENTES,
            {
                "q": q,
                "patron": _patron(q),
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        return _con_total(filas)

    def cursos_de_docente(self, sesion: Session, docente_id: str) -> list[Fila]:
        return filas_sql(sesion, CURSOS_DE_DOCENTE, {"id": docente_id})

    def listar_cursos(  # noqa: PLR0913
        self,
        sesion: Session,
        *,
        docente_id: str | None,
        sin_docente: bool,
        estado: str | None,
        q: str | None,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            CURSOS,
            {
                "docente": docente_id,
                "sin_docente": sin_docente,
                "estado": estado,
                "q": q,
                "patron": _patron(q),
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        return _con_total(filas)
