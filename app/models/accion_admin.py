from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ACCIONES_ADMIN
from app.models.base import Base, en_lista


class AccionAdmin(Base):
    """Auditoria de lo que un administrador hace sobre una cuenta (HU-B-405).

    `usuario_id` no tiene FK: la auditoria sobrevive a la cuenta eliminada. El detalle nunca
    lleva contrasenas, codigos ni el correo completo de una cuenta eliminada.
    """

    __tablename__ = "acciones_admin"
    __table_args__ = (
        CheckConstraint(en_lista("accion", ACCIONES_ADMIN), name="accion"),
        CheckConstraint("jsonb_typeof(detalle) = 'object'", name="detalle"),
        Index("ix_acciones_admin_usuario_creado", "usuario_id", "creado_en"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    # SET NULL: si el administrador se elimina, la auditoria se conserva.
    admin_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    usuario_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    accion: Mapped[str] = mapped_column(Text)
    detalle: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
