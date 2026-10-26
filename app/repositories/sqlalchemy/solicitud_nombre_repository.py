# =========================================================
# Solicitudes de cambio de nombre (HU-B-415). Consultas fijas, sin correos. No abre ni confirma
# transacciones: usa la sesion del servicio.
# =========================================================
from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

PENDIENTE_DE = """
select 1 from public.solicitudes_nombre
where usuario_id = cast(:usuario as uuid) and estado = 'pendiente'
"""

CREAR = """
insert into public.solicitudes_nombre (usuario_id, mensaje)
values (cast(:usuario as uuid), :mensaje)
returning id, estado, creado_en
"""

ULTIMA_DE = """
select id, estado, mensaje, creado_en, resuelta_en
from public.solicitudes_nombre
where usuario_id = cast(:usuario as uuid)
order by creado_en desc
limit 1
"""

# Panel del admin: quien la envio (nombre y rol, no el correo), el texto y el estado actual.
LISTA = """
select s.id, s.usuario_id, p.nombre, p.apellido, p.rol, p.puede_editar_nombre,
  s.mensaje, s.estado, s.creado_en, s.resuelta_en,
  r.nombre as resuelta_por_nombre, r.apellido as resuelta_por_apellido
from public.solicitudes_nombre s
join public.profiles p on p.id = s.usuario_id
left join public.profiles r on r.id = s.resuelta_por
where (cast(:estado as text) is null or s.estado = cast(:estado as text))
  and (cast(:rol as text) is null or p.rol = cast(:rol as text))
order by (s.estado <> 'pendiente'), coalesce(s.resuelta_en, s.creado_en) desc, s.id
"""

# Pendientes, aceptadas y rechazadas de cada rol: las pestanas no dependen de los filtros.
TOTALES = """
select p.rol, s.estado, count(*)::int as total
from public.solicitudes_nombre s
join public.profiles p on p.id = s.usuario_id
group by p.rol, s.estado
"""

OBTENER = """
select id, usuario_id, estado
from public.solicitudes_nombre
where id = cast(:id as uuid)
for update
"""

RESOLVER = """
update public.solicitudes_nombre
set estado = :estado, resuelta_en = now(), resuelta_por = cast(:por as uuid)
where id = cast(:id as uuid) and estado = 'pendiente'
returning id, usuario_id, estado, resuelta_en
"""


class SqlSolicitudNombreRepository:
    def hay_pendiente(self, sesion: Session, usuario_id: str) -> bool:
        return bool(filas_sql(sesion, PENDIENTE_DE, {"usuario": usuario_id}))

    def crear(self, sesion: Session, usuario_id: str, mensaje: str) -> Fila:
        return filas_sql(sesion, CREAR, {"usuario": usuario_id, "mensaje": mensaje})[0]

    def ultima_de(self, sesion: Session, usuario_id: str) -> Fila | None:
        filas = filas_sql(sesion, ULTIMA_DE, {"usuario": usuario_id})
        return filas[0] if filas else None

    def listar(self, sesion: Session, estado: str | None, rol: str | None) -> list[Fila]:
        return filas_sql(sesion, LISTA, {"estado": estado, "rol": rol})

    def totales(self, sesion: Session) -> dict[str, dict[str, int]]:
        por_rol = {
            rol: {"pendiente": 0, "aceptada": 0, "rechazada": 0}
            for rol in ("estudiante", "docente")
        }
        for fila in filas_sql(sesion, TOTALES, {}):
            if fila["rol"] in por_rol:
                por_rol[fila["rol"]][fila["estado"]] = fila["total"]
        return por_rol

    def obtener_para_resolver(self, sesion: Session, solicitud_id: str) -> Fila | None:
        filas = filas_sql(sesion, OBTENER, {"id": solicitud_id})
        return filas[0] if filas else None

    def resolver(self, sesion: Session, solicitud_id: str, estado: str, por: str) -> Fila | None:
        filas = filas_sql(sesion, RESOLVER, {"id": solicitud_id, "estado": estado, "por": por})
        return filas[0] if filas else None
