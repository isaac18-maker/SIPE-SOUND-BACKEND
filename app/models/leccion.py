from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ESTADOS_CONTENIDO
from app.models.base import (
    NIVELES,
    AutoriaMixin,
    Base,
    CreadoEnMixin,
    EstadoMixin,
    en_lista,
    existente,
)


class Leccion(CreadoEnMixin, EstadoMixin, AutoriaMixin, Base):
    __tablename__ = "lecciones"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("lecciones_pkey")),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("lecciones_nivel_check")),
        CheckConstraint(en_lista("estado", ESTADOS_CONTENIDO), name="estado"),
        CheckConstraint(
            "(estado = 'archivado') = (archivado_en IS NOT NULL)", name="archivado_coherente"
        ),
        CheckConstraint("duracion_min IS NULL OR duracion_min > 0", name="duracion_min"),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    # TODO(HU-B-312): retirar `duracion` (texto) cuando el frontend use duracion_min.
    duracion: Mapped[str | None] = mapped_column(Text)
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    temas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    contenido: Mapped[str | None] = mapped_column(Text)
    # Una leccion pertenece a su bloque: si se borra el bloque, se borran sus lecciones.
    bloque_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bloques.id", ondelete="CASCADE"), index=True
    )
