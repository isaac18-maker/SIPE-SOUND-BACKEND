from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SolicitudInscripcion(Base):
    """Un estudiante pide entrar a un curso; el docente o un admin la resuelve (HU-B-414)."""

    __tablename__ = "solicitudes_inscripcion"
    __table_args__ = (
        CheckConstraint("estado in ('pendiente', 'aceptada', 'rechazada')", name="estado"),
        CheckConstraint(
            "(estado = 'pendiente') = (resuelta_en is null)", name="resolucion_coherente"
        ),
        # Una sola pendiente por curso y estudiante; las resueltas quedan como historial.
        Index(
            "uq_solicitudes_inscripcion_pendiente",
            "curso_id",
            "estudiante_id",
            unique=True,
            postgresql_where=text("estado = 'pendiente'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    curso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cursos.id", ondelete="CASCADE"), index=True
    )
    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    estado: Mapped[str] = mapped_column(Text, server_default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resuelta_por: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
