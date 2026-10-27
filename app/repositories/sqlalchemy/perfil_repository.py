from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.models.curso import Curso
from app.models.profile import Profile
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila

EMAIL_DE = text("select email from auth.users where id = :id")


class SqlPerfilRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def obtener(self, sesion: Session, usuario_id: str) -> Fila | None:
        perfil = sesion.get(Profile, usuario_id)
        return a_fila(perfil) if perfil else None

    def contar_cursos_activos_a_cargo(self, sesion: Session, usuario_id: str) -> int:
        consulta = (
            select(func.count())
            .select_from(Curso)
            .where(Curso.docente_id == usuario_id, Curso.archivado_en.is_(None))
        )
        return sesion.scalar(consulta) or 0

    def email_de(self, sesion: Session, usuario_id: str) -> str | None:
        """El correo vigente (el del JWT queda viejo tras un cambio de correo)."""
        return sesion.execute(EMAIL_DE, {"id": usuario_id}).scalar()

    def obtener_para_actualizar(self, sesion: Session, usuario_id: str) -> Fila | None:
        """Bloquea la fila hasta el fin de la transaccion (select ... for update)."""
        perfil = sesion.get(Profile, usuario_id, with_for_update=True)
        return a_fila(perfil) if perfil else None

    def actualizar_nombre(self, sesion: Session, usuario_id: str, cambios: dict[str, str]) -> Fila:
        perfil = sesion.get(Profile, usuario_id)
        for campo, valor in cambios.items():
            setattr(perfil, campo, valor)
        perfil.actualizado_en = func.now()
        sesion.flush()
        sesion.refresh(perfil)
        return a_fila(perfil)

    def actualizar_permiso_nombre(
        self, sesion: Session, usuario_ids: list[str], permitido: bool
    ) -> list[str]:
        """Devuelve los ids que existen y se actualizaron (los demas se ignoran)."""
        consulta = (
            update(Profile)
            .where(Profile.id.in_(usuario_ids))
            .values(puede_editar_nombre=permitido, actualizado_en=func.now())
            .returning(Profile.id)
        )
        return [str(fila[0]) for fila in sesion.execute(consulta)]

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
