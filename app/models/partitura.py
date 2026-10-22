from sqlalchemy import ARRAY, CheckConstraint, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente

TIPOS_PARTITURA = ("partitura", "tablatura", "ambas")


class Partitura(CreadoEnMixin, Base):
    __tablename__ = "partituras"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("partituras_pkey")),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("partituras_nivel_check")),
        CheckConstraint(en_lista("tipo", TIPOS_PARTITURA), name=existente("partituras_tipo_check")),
    )

    id: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    artista: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str | None] = mapped_column(Text, server_default="principiante")
    tipo: Mapped[str | None] = mapped_column(Text)
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    imagen_url: Mapped[str | None] = mapped_column(Text)
