from typing import Any

from sqlalchemy import CheckConstraint, Integer, PrimaryKeyConstraint, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.longitudes import DESCRIPCION_ACORDE_MAX, NOMBRE_ACORDE_MAX, NOMBRE_ACORDE_MIN
from app.models.base import Base, CreadoEnMixin, en_lista, existente, largo_entre, largo_maximo

TIPOS_ACORDE = ("mayor", "menor", "septima", "disminuido")
DIFICULTADES = ("facil", "medio", "dificil")


class Acorde(CreadoEnMixin, Base):
    __tablename__ = "acordes"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("acordes_pkey")),
        UniqueConstraint("nombre", name=existente("acordes_nombre_key")),
        CheckConstraint(
            en_lista("dificultad", DIFICULTADES), name=existente("acordes_dificultad_check")
        ),
        CheckConstraint(en_lista("tipo", TIPOS_ACORDE), name=existente("acordes_tipo_check")),
        CheckConstraint(largo_entre("nombre", NOMBRE_ACORDE_MIN, NOMBRE_ACORDE_MAX), name="nombre"),
        CheckConstraint(largo_maximo("descripcion", DESCRIPCION_ACORDE_MAX), name="descripcion"),
    )

    id: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str | None] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    dificultad: Mapped[str | None] = mapped_column(Text, server_default="facil")
    diagram: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
