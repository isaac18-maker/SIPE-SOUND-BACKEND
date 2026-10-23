from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.longitudes import EMAIL_MAX
from app.models.base import Base


class DocentePreautorizado(Base):
    """Correo que un admin autoriza como docente (HU-B-321).

    Al confirmar su correo, la cuenta con ese email recibe el rol 'docente'
    (funcion public.aplicar_docente_preautorizado, revision 0014).
    """

    __tablename__ = "docentes_preautorizados"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email))", name="email_normalizado"),
        CheckConstraint(f"char_length(email) <= {EMAIL_MAX}", name="email_largo"),
        CheckConstraint(
            "email ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$'", name="email_formato"
        ),
        CheckConstraint("(usado_en IS NULL) = (usuario_id IS NULL)", name="uso_coherente"),
    )

    email: Mapped[str] = mapped_column(Text, primary_key=True)
    # SET NULL: si el admin o el docente se eliminan, el registro de auditoria sigue.
    creado_por: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
