from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CODIGO_INTENTOS_MAX, PROPOSITOS_CODIGO
from app.core.longitudes import EMAIL_MAX
from app.models.base import Base, en_lista


class CodigoVerificacion(Base):
    """Codigo o token de un solo uso (HU-B-402). Solo guarda su HMAC, nunca el valor."""

    __tablename__ = "codigos_verificacion"
    __table_args__ = (
        CheckConstraint(en_lista("proposito", PROPOSITOS_CODIGO), name="proposito"),
        CheckConstraint("codigo_hash ~ '^[0-9a-f]{64}$'", name="codigo_hash"),
        CheckConstraint(f"char_length(email_destino) <= {EMAIL_MAX}", name="email_destino"),
        CheckConstraint(f"intentos BETWEEN 0 AND {CODIGO_INTENTOS_MAX}", name="intentos"),
        # Tope de vigencia en la base: ni un error del backend puede emitir un codigo eterno.
        CheckConstraint(
            "expira_en > creado_en AND expira_en <= creado_en + interval '15 minutes'",
            name="vigencia",
        ),
        CheckConstraint("usado_en IS NULL OR invalidado_en IS NULL", name="cerrado_una_vez"),
        # Un solo codigo ABIERTO por persona y proposito.
        Index(
            "uq_codigos_verificacion_abierto",
            "usuario_id",
            "proposito",
            unique=True,
            postgresql_where=text("usado_en IS NULL AND invalidado_en IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    usuario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    proposito: Mapped[str] = mapped_column(Text)
    codigo_hash: Mapped[str] = mapped_column(Text)
    # Correo al que se envio (en cambiar_correo, el nuevo).
    email_destino: Mapped[str | None] = mapped_column(Text)
    intentos: Mapped[int] = mapped_column(Integer, server_default="0")
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
