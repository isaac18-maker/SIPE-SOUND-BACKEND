from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ESTADOS_ENVIO, TIPOS_CORREO
from app.models.base import Base, en_lista


class EnvioCorreo(Base):
    """Resultado de cada correo que sale (HU-B-401). Nunca guarda codigos, enlaces ni cuerpos."""

    __tablename__ = "envios_correo"
    __table_args__ = (
        CheckConstraint(en_lista("tipo", TIPOS_CORREO), name="tipo"),
        CheckConstraint(en_lista("estado", ESTADOS_ENVIO), name="estado"),
        CheckConstraint("error ~ '^[a-z_]{1,40}$'", name="error_formato"),
        CheckConstraint("(estado = 'fallido') = (error IS NOT NULL)", name="error_coherente"),
        # Cubre la FK usuario_id y la consulta "ultimo envio de este tipo a esta persona".
        Index("ix_envios_correo_usuario_tipo_creado", "usuario_id", "tipo", "creado_en"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    # SET NULL: la bitacora sobrevive a la cuenta eliminada.
    usuario_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    tipo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
