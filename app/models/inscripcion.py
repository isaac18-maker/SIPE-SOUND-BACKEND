from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Inscripcion(Base):
    """Un estudiante en un curso. Se borra con el curso o con el estudiante."""

    __tablename__ = "inscripciones"
    __table_args__ = (UniqueConstraint("curso_id", "estudiante_id"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    curso_id: Mapped[int] = mapped_column(Integer, ForeignKey("cursos.id", ondelete="CASCADE"))
    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    inscrito_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
