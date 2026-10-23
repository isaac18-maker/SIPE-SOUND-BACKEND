from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ROLES
from app.core.longitudes import NOMBRE_PERSONA_MAX, NOMBRE_PERSONA_MIN
from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente, largo_entre


class Profile(CreadoEnMixin, Base):
    """Lo crea el trigger on_auth_user_created al registrarse un usuario."""

    __tablename__ = "profiles"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("profiles_pkey")),
        ForeignKeyConstraint(
            ["id"], ["auth.users.id"], ondelete="CASCADE", name=existente("profiles_id_fkey")
        ),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("profiles_nivel_check")),
        CheckConstraint(en_lista("rol", ROLES), name="rol"),
        CheckConstraint(
            largo_entre("nombre", NOMBRE_PERSONA_MIN, NOMBRE_PERSONA_MAX), name="nombre"
        ),
        # Sin caracteres de control (saltos de linea, tabuladores, NUL...).
        CheckConstraint("nombre !~ '[[:cntrl:]]'", name="nombre_sin_control"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    nombre: Mapped[str] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    rol: Mapped[str] = mapped_column(Text, server_default="estudiante")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
