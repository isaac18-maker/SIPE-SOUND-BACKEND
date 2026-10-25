from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.accion_admin import AccionAdmin
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

ULTIMAS = text(
    "select a.accion, a.detalle, a.creado_en, p.nombre as admin "
    "from public.acciones_admin a left join public.profiles p on p.id = a.admin_id "
    "where a.usuario_id = cast(:id as uuid) "
    "order by a.creado_en desc limit :limite"
)


class SqlAccionAdminRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def registrar(
        self,
        sesion: Session,
        *,
        admin_id: str,
        usuario_id: str,
        accion: str,
        detalle: dict[str, Any] | None = None,
    ) -> None:
        sesion.add(
            AccionAdmin(
                admin_id=admin_id, usuario_id=usuario_id, accion=accion, detalle=detalle or {}
            )
        )
        sesion.flush()

    def ultimas(self, sesion: Session, usuario_id: str, limite: int) -> list[Fila]:
        return filas_sql(sesion, ULTIMAS, {"id": usuario_id, "limite": limite})
