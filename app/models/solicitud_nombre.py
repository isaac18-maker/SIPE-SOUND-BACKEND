from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SolicitudNombre(Base):
    """Pide que un administrador habilite el cambio de nombre de la cuenta (HU-B-415)."""

    __tablename__ = "solicitudes_nombre"
    __table_args__ = (
        CheckConstraint("estado in ('pendiente', 'aceptada', 'rechazada')", name="estado"),
        CheckConstraint("char_length(btrim(mensaje)) between 1 and 1000", name="mensaje"),
        CheckConstraint(
            "(estado = 'pendiente') = (resuelta_en is null)", name="resolucion_coherente"
        ),
        # Una sola pendiente por persona; las resueltas quedan como historial.
        Index(
            "uq_solicitudes_nombre_pendiente",
            "usuario_id",
            unique=True,
            postgresql_where=text("estado = 'pendiente'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    usuario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    mensaje: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, server_default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resuelta_por: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
