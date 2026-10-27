from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.constants import TIPO_TERMINOS
from app.models.documento_legal import DocumentoLegal
from app.models.profile import Profile
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import formatear_fecha


class SqlTerminosRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def vigente(self, sesion: Session) -> Fila:
        """El texto vigente con el nombre de quien lo modifico por ultima vez (o None)."""
        consulta = (
            select(
                DocumentoLegal.version,
                DocumentoLegal.contenido,
                DocumentoLegal.actualizado_en,
                Profile.nombre,
                Profile.apellido,
            )
            .select_from(DocumentoLegal)
            .outerjoin(Profile, Profile.id == DocumentoLegal.actualizado_por)
            .where(DocumentoLegal.tipo == TIPO_TERMINOS)
        )
        fila = sesion.execute(consulta).one()
        return {
            "version": fila.version,
            "contenido": fila.contenido,
            "actualizado_en": formatear_fecha(fila.actualizado_en),
            "actualizado_por": (
                " ".join(p for p in (fila.nombre, fila.apellido) if p) if fila.nombre else None
            ),
        }

    def version_vigente(self, sesion: Session) -> int:
        return sesion.scalar(
            select(DocumentoLegal.version).where(DocumentoLegal.tipo == TIPO_TERMINOS)
        )

    def reemplazar(
        self, sesion: Session, contenido: str, *, nueva_version: bool, admin_id: str
    ) -> None:
        """Guarda el texto; con `nueva_version` sube el numero y todos deben volver a aceptarlo."""
        valores = {
            "contenido": contenido,
            "actualizado_por": admin_id,
            "actualizado_en": func.now(),
        }
        if nueva_version:
            valores["version"] = DocumentoLegal.version + 1
        sesion.execute(
            update(DocumentoLegal).where(DocumentoLegal.tipo == TIPO_TERMINOS).values(**valores)
        )

    def aceptar(self, sesion: Session, usuario_id: str, version: int) -> None:
        sesion.execute(
            update(Profile)
            .where(Profile.id == usuario_id)
            .values(terminos_version=version, terminos_aceptados_en=func.now())
        )
