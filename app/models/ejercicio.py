from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
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


class Ejercicio(CreadoEnMixin, EstadoMixin, AutoriaMixin, Base):
    __tablename__ = "ejercicios"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("ejercicios_pkey")),
        # El ejercicio puede existir suelto en la biblioteca si se borra su leccion.
        ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            ondelete="SET NULL",
            name=existente("ejercicios_leccion_id_fkey"),
        ),
        Index("ix_ejercicios_leccion_id", "leccion_id"),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("ejercicios_nivel_check")),
        CheckConstraint(en_lista("estado", ESTADOS_CONTENIDO), name="estado"),
        CheckConstraint(
            "(estado = 'archivado') = (archivado_en IS NOT NULL)", name="archivado_coherente"
        ),
        CheckConstraint("duracion_min IS NULL OR duracion_min > 0", name="duracion_min"),
    )

    id: Mapped[int] = mapped_column(Integer)
    leccion_id: Mapped[int | None] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    bpm_recomendado: Mapped[int | None] = mapped_column(Integer, server_default="60")
    # TODO(HU-B-312): retirar `duracion` (texto) cuando el frontend use duracion_min.
    duracion: Mapped[str | None] = mapped_column(Text)
    compas: Mapped[str | None] = mapped_column(Text, server_default="4/4")
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    pasos: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
