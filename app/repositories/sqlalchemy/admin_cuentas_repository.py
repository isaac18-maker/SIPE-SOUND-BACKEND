from typing import Any

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

# El estado de una cuenta se CALCULA (00-decisiones-fase-4, seccion 3): suspendida gana sobre
# pendiente. Es la misma expresion en el listado, el detalle y los totales.
ESTADO_SQL = """case when p.suspendido_en is not null then 'suspendida'
         when p.correo_verificado_en is null then 'pendiente_verificacion'
         else 'activa' end"""

COLUMNAS = f"""
  p.id, p.nombre, p.apellido, u.email, p.rol, p.puede_editar_nombre, p.creado_en,
  p.correo_verificado_en, p.suspendido_en, p.motivo_suspension,
  u.last_sign_in_at as ultimo_acceso,
  {ESTADO_SQL} as estado,
  (select jsonb_build_object('estado', e.estado, 'creado_en', e.creado_en)
     from public.envios_correo e
    where e.usuario_id = p.id and e.tipo = 'verificar_correo'
    order by e.creado_en desc limit 1) as ultimo_envio_verificacion,
  case when p.rol = 'docente'
    then (select count(*) from public.cursos c
           where c.docente_id = p.id and c.archivado_en is null)
    else (select count(*) from public.inscripciones i
            join public.cursos c on c.id = i.curso_id
           where i.estudiante_id = p.id and c.archivado_en is null)
  end as cursos"""  # noqa: S608 - fragmento constante

# Una sola sentencia para la pagina (count(*) over () da el total), como SqlSeguimientoRepository.
LISTADO = f"""
with base as (
  select {COLUMNAS}
  from public.profiles p join auth.users u on u.id = p.id
  where (cast(:rol as text) is null or p.rol = :rol)
    and (cast(:permiso as boolean) is null or p.puede_editar_nombre = :permiso)
    and (cast(:q as text) is null or p.nombre ilike :patron or p.apellido ilike :patron
         or u.email ilike :patron)
)
select base.*, count(*) over () as total_filas
from base
where (cast(:estado as text) is null or base.estado = :estado)
order by {{orden}}
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

# El ORDER BY sale de un diccionario cerrado; los valores del usuario van como parametros.
ORDENES = {
    "nombre": "base.nombre asc, base.apellido asc nulls last, base.id",
    "-creado_en": "base.creado_en desc, base.id",
    "-ultimo_acceso": "base.ultimo_acceso desc nulls last, base.id",
}

DETALLE = f"""
select {COLUMNAS}
from public.profiles p join auth.users u on u.id = p.id
where p.id = cast(:id as uuid)
"""  # noqa: S608 - solo fragmentos constantes

TOTALES = f"""
select {ESTADO_SQL} as estado, count(*) as n
from public.profiles p
group by 1
"""  # noqa: S608 - solo fragmentos constantes

INSCRIPCIONES = """
select i.curso_id, c.nombre as curso, d.nombre as docente, d.apellido as docente_apellido,
       i.inscrito_en
from public.inscripciones i
join public.cursos c on c.id = i.curso_id
join public.profiles d on d.id = c.docente_id
where i.estudiante_id = cast(:id as uuid) and c.archivado_en is null
order by i.inscrito_en desc
"""

CURSOS_A_CARGO = """
select c.id, c.nombre, c.archivado_en,
       (select count(*) from public.inscripciones i where i.curso_id = c.id) as estudiantes
from public.cursos c
where c.docente_id = cast(:id as uuid)
order by (c.archivado_en is not null), c.nombre
"""

CONTAR_CURSOS_A_CARGO = """
select count(*) as n from public.cursos where docente_id = cast(:id as uuid)
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAdminCuentasRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def listar(
        self,
        sesion: Session,
        *,
        rol: str | None,
        estado: str | None,
        q: str | None,
        puede_editar_nombre: bool | None,
        orden: str,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            LISTADO.format(orden=ORDENES[orden]),
            {
                "rol": rol,
                "estado": estado,
                "q": q,
                "patron": f"%{_escapar_like(q)}%" if q else None,
                "permiso": puede_editar_nombre,
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        total = filas[0]["total_filas"] if filas else 0
        for fila in filas:
            fila.pop("total_filas")
        return filas, total

    def totales_por_estado(self, sesion: Session) -> dict[str, int]:
        filas = filas_sql(sesion, TOTALES, {})
        return {fila["estado"]: int(fila["n"]) for fila in filas}

    def obtener(self, sesion: Session, usuario_id: str) -> Fila | None:
        filas = filas_sql(sesion, DETALLE, {"id": usuario_id})
        return filas[0] if filas else None

    def inscripciones(self, sesion: Session, usuario_id: str) -> list[Fila]:
        return filas_sql(sesion, INSCRIPCIONES, {"id": usuario_id})

    def cursos_a_cargo(self, sesion: Session, usuario_id: str) -> list[Fila]:
        return filas_sql(sesion, CURSOS_A_CARGO, {"id": usuario_id})

    def contar_cursos_a_cargo(self, sesion: Session, usuario_id: str) -> int:
        return int(filas_sql(sesion, CONTAR_CURSOS_A_CARGO, {"id": usuario_id})[0]["n"])

    def suspender(self, sesion: Session, usuario_id: str, motivo: str) -> None:
        self._actualizar(sesion, usuario_id, suspendido_en=func.now(), motivo_suspension=motivo)

    def reactivar(self, sesion: Session, usuario_id: str) -> None:
        self._actualizar(sesion, usuario_id, suspendido_en=None, motivo_suspension=None)

    @staticmethod
    def _actualizar(sesion: Session, usuario_id: str, **valores: Any) -> None:
        sesion.execute(
            update(Profile)
            .where(Profile.id == usuario_id)
            .values(actualizado_en=func.now(), **valores)
        )
