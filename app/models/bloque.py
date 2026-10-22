from sqlalchemy import CheckConstraint, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente


class Bloque(CreadoEnMixin, Base):
    __tablename__ = "bloques"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("bloques_pkey")),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("bloques_nivel_check")),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    orden_index: Mapped[int] = mapped_column(Integer)
