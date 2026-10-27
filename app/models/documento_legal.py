from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import TERMINOS_MAX, TIPO_TERMINOS
from app.models.base import Base


class DocumentoLegal(Base):
    """Texto legal vigente en Markdown (HU-B-411). Hoy solo "terminos"; `version` sube cuando el
    administrador exige que todas las cuentas lo vuelvan a aceptar."""

    __tablename__ = "documentos_legales"
    __table_args__ = (
        CheckConstraint("tipo = '" + TIPO_TERMINOS + "'", name="tipo"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint(
            f"char_length(btrim(contenido)) BETWEEN 1 AND {TERMINOS_MAX}", name="contenido"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(Text, unique=True, server_default=TIPO_TERMINOS)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    contenido: Mapped[str] = mapped_column(Text)
    # Quien lo modifico por ultima vez; SET NULL si su cuenta se elimina (contrato de BD, secc. 4).
    actualizado_por: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
