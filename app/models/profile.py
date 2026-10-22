from sqlalchemy import CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente


class Profile(CreadoEnMixin, Base):
    """Lo crea el trigger on_auth_user_created al registrarse un usuario."""

    __tablename__ = "profiles"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("profiles_pkey")),
        ForeignKeyConstraint(
            ["id"], ["auth.users.id"], ondelete="CASCADE", name=existente("profiles_id_fkey")
        ),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("profiles_nivel_check")),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    nombre: Mapped[str] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
