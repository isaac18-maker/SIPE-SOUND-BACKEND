from sqlalchemy import CheckConstraint, Integer, PrimaryKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ESTADOS_CONTENIDO
from app.models.base import NIVELES, Base, CreadoEnMixin, EstadoMixin, en_lista, existente


class Bloque(CreadoEnMixin, EstadoMixin, Base):
    __tablename__ = "bloques"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("bloques_pkey")),
        UniqueConstraint("orden_index"),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("bloques_nivel_check")),
        CheckConstraint(en_lista("estado", ESTADOS_CONTENIDO), name="estado"),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    orden_index: Mapped[int] = mapped_column(Integer)
