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
from app.core.longitudes import (
    BPM_MAXIMO,
    BPM_MINIMO,
    DESCRIPCION_MAX,
    DURACION_MIN_MAXIMO,
    DURACION_MIN_MINIMO,
    MAXIMO_ACORDES,
    MAXIMO_PASOS,
    NOMBRE_ACORDE_MAX,
    PASO_MAX,
    PATRON_COMPAS,
    TITULO_MAX,
    TITULO_MIN,
)
from app.models.base import (
    NIVELES,
    AutoriaMixin,
    Base,
    CreadoEnMixin,
    EstadoMixin,
    elementos_caben,
    elementos_maximo,
    en_lista,
    entero_entre,
    existente,
    largo_entre,
    largo_maximo,
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
        CheckConstraint(
            entero_entre("duracion_min", DURACION_MIN_MINIMO, DURACION_MIN_MAXIMO),
            name="duracion_min",
        ),
        CheckConstraint(largo_entre("nombre", TITULO_MIN, TITULO_MAX), name="nombre"),
        CheckConstraint(largo_maximo("descripcion", DESCRIPCION_MAX), name="descripcion"),
        CheckConstraint(
            entero_entre("bpm_recomendado", BPM_MINIMO, BPM_MAXIMO), name="bpm_recomendado"
        ),
        CheckConstraint(f"compas ~ '{PATRON_COMPAS}'", name="compas"),
        CheckConstraint(elementos_maximo("acordes", MAXIMO_ACORDES), name="acordes"),
        CheckConstraint(elementos_maximo("pasos", MAXIMO_PASOS), name="pasos"),
        CheckConstraint(elementos_caben("acordes", NOMBRE_ACORDE_MAX), name="acordes_largo"),
        CheckConstraint(elementos_caben("pasos", PASO_MAX), name="pasos_largo"),
    )

    id: Mapped[int] = mapped_column(Integer)
    leccion_id: Mapped[int | None] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    bpm_recomendado: Mapped[int | None] = mapped_column(Integer, server_default="60")
    compas: Mapped[str | None] = mapped_column(Text, server_default="4/4")
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    pasos: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
