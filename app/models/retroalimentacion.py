from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Retroalimentacion(Base):
    """Comentario de un docente a un estudiante dentro de un curso."""

    __tablename__ = "retroalimentaciones"
    __table_args__ = (CheckConstraint("char_length(mensaje) BETWEEN 1 AND 1000", name="mensaje"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    curso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cursos.id", ondelete="CASCADE"), index=True
    )
    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    # SET NULL: si el docente se elimina, el comentario sigue siendo util al estudiante.
    docente_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    mensaje: Mapped[str] = mapped_column(Text)
    leida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
