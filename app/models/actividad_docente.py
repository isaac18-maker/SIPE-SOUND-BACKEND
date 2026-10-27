from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ACCIONES_ACTIVIDAD, TIPOS_ACTIVIDAD
from app.models.base import Base, en_lista


class ActividadDocente(Base):
    """Que hizo un docente y en que curso (HU-B-418). Nunca guarda contenido ni datos de
    estudiantes. RLS activo y sin politicas: solo el backend."""

    __tablename__ = "actividad_docente"
    __table_args__ = (
        CheckConstraint(en_lista("tipo", TIPOS_ACTIVIDAD), name="tipo"),
        CheckConstraint(en_lista("accion", ACCIONES_ACTIVIDAD), name="accion"),
        Index("ix_actividad_docente_docente_creado", "docente_id", text("creado_en DESC")),
        Index("ix_actividad_docente_curso_creado", "curso_id", text("creado_en DESC")),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    docente_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE")
    )
    # SET NULL: la actividad sobrevive a un curso que se borre.
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("cursos.id", ondelete="SET NULL"))
    tipo: Mapped[str] = mapped_column(Text)
    accion: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
