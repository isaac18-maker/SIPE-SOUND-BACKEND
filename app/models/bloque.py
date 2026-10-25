from sqlalchemy import CheckConstraint, Integer, PrimaryKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ESTADOS_CONTENIDO
from app.core.longitudes import DESCRIPCION_MAX, TITULO_MAX, TITULO_MIN
from app.models.base import (
    NIVELES,
    Base,
    CreadoEnMixin,
    EstadoMixin,
    VideoMixin,
    en_lista,
    existente,
    largo_entre,
    largo_maximo,
    restricciones_video,
)


class Bloque(CreadoEnMixin, EstadoMixin, VideoMixin, Base):
    __tablename__ = "bloques"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("bloques_pkey")),
        UniqueConstraint("orden_index"),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("bloques_nivel_check")),
        CheckConstraint(en_lista("estado", ESTADOS_CONTENIDO), name="estado"),
        CheckConstraint(largo_entre("titulo", TITULO_MIN, TITULO_MAX), name="titulo"),
        CheckConstraint(largo_maximo("descripcion", DESCRIPCION_MAX), name="descripcion"),
        *restricciones_video(),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    orden_index: Mapped[int] = mapped_column(Integer)
