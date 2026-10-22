from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, en_lista, existente

TIPOS_PROGRESO = ("leccion", "ejercicio", "bloque")


class Progreso(Base):
    """Tabla polimorfica (tipo + contenido_id), sin FK al contenido: HU-B-305 la reemplaza."""

    __tablename__ = "progreso"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("progreso_pkey")),
        UniqueConstraint(
            "usuario_id",
            "tipo",
            "contenido_id",
            name=existente("progreso_usuario_id_tipo_contenido_id_key"),
        ),
        ForeignKeyConstraint(
            ["usuario_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name=existente("progreso_usuario_id_fkey"),
        ),
        CheckConstraint(
            "porcentaje >= 0 and porcentaje <= 100", name=existente("progreso_porcentaje_check")
        ),
        CheckConstraint(en_lista("tipo", TIPOS_PROGRESO), name=existente("progreso_tipo_check")),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), server_default=func.gen_random_uuid())
    usuario_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    tipo: Mapped[str] = mapped_column(Text)
    contenido_id: Mapped[int] = mapped_column(Integer)
    porcentaje: Mapped[int] = mapped_column(Integer, server_default="0")
    completado: Mapped[bool | None] = mapped_column(Boolean, server_default=text("false"))
    actualizado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
