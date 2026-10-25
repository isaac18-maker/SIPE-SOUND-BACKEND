from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila

EMAIL_DE = text("select email from auth.users where id = :id")


class SqlPerfilRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def obtener(self, sesion: Session, usuario_id: str) -> Fila | None:
        perfil = sesion.get(Profile, usuario_id)
        return a_fila(perfil) if perfil else None

    def email_de(self, sesion: Session, usuario_id: str) -> str | None:
        """El correo vigente (el del JWT queda viejo tras un cambio de correo)."""
        return sesion.execute(EMAIL_DE, {"id": usuario_id}).scalar()

    def obtener_para_actualizar(self, sesion: Session, usuario_id: str) -> Fila | None:
        """Bloquea la fila hasta el fin de la transaccion (select ... for update)."""
        perfil = sesion.get(Profile, usuario_id, with_for_update=True)
        return a_fila(perfil) if perfil else None

    def contar_por_rol(self, sesion: Session, rol: str) -> int:
        # Bloquea las filas contadas para que dos cambios simultaneos no dejen
        # el sistema sin administradores.
        ids = select(Profile.id).where(Profile.rol == rol).with_for_update()
        return sesion.scalar(select(func.count()).select_from(ids.subquery())) or 0

    def actualizar_rol(self, sesion: Session, usuario_id: str, rol: str) -> Fila:
        perfil = sesion.get(Profile, usuario_id)
        perfil.rol = rol
        sesion.flush()
        sesion.refresh(perfil)
        return a_fila(perfil)
