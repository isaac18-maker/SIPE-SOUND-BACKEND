from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NIVELES, Base, en_lista


class Curso(Base):
    """Grupo de estudiantes a cargo de un docente; se ingresa con un codigo."""

    __tablename__ = "cursos"
    __table_args__ = (
        UniqueConstraint("codigo_invitacion"),
        CheckConstraint(en_lista("nivel", NIVELES), name="nivel"),
        CheckConstraint("char_length(nombre) BETWEEN 3 AND 120", name="nombre"),
        CheckConstraint("codigo_invitacion ~ '^[A-HJKMNP-Z2-9]{8}$'", name="codigo_invitacion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    # RESTRICT: un curso no puede quedar sin docente; primero se reasigna.
    docente_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="RESTRICT"), index=True
    )
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    codigo_invitacion: Mapped[str] = mapped_column(Text)
    archivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
