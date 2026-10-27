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
from app.core.longitudes import (
    CONTENIDO_LECCION_MAX,
    DESCRIPCION_MAX,
    DURACION_MIN_MAXIMO,
    DURACION_MIN_MINIMO,
    MAXIMO_ACORDES,
    MAXIMO_TEMAS,
    NOMBRE_ACORDE_MAX,
    TEMA_MAX,
    TITULO_MAX,
    TITULO_MIN,
)
from app.models.base import (
    NIVELES,
    AutoriaMixin,
    Base,
    CreadoEnMixin,
    EstadoMixin,
    VideoMixin,
    elementos_caben,
    elementos_maximo,
    en_lista,
    entero_entre,
    existente,
    largo_entre,
    largo_maximo,
    restricciones_video,
)


class Leccion(CreadoEnMixin, EstadoMixin, AutoriaMixin, VideoMixin, Base):
    __tablename__ = "lecciones"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("lecciones_pkey")),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("lecciones_nivel_check")),
        CheckConstraint(en_lista("estado", ESTADOS_CONTENIDO), name="estado"),
        CheckConstraint(
            "(estado = 'archivado') = (archivado_en IS NOT NULL)", name="archivado_coherente"
        ),
        CheckConstraint(
            entero_entre("duracion_min", DURACION_MIN_MINIMO, DURACION_MIN_MAXIMO),
            name="duracion_min",
        ),
        CheckConstraint(largo_entre("titulo", TITULO_MIN, TITULO_MAX), name="titulo"),
        CheckConstraint(largo_maximo("descripcion", DESCRIPCION_MAX), name="descripcion"),
        CheckConstraint(largo_maximo("contenido", CONTENIDO_LECCION_MAX), name="contenido"),
        CheckConstraint(elementos_maximo("acordes", MAXIMO_ACORDES), name="acordes"),
        CheckConstraint(elementos_maximo("temas", MAXIMO_TEMAS), name="temas"),
        CheckConstraint(elementos_caben("acordes", NOMBRE_ACORDE_MAX), name="acordes_largo"),
        CheckConstraint(elementos_caben("temas", TEMA_MAX), name="temas_largo"),
        *restricciones_video(),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    temas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    contenido: Mapped[str | None] = mapped_column(Text)
    # Una leccion pertenece a su bloque: si se borra el bloque, se borran sus lecciones.
    bloque_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bloques.id", ondelete="CASCADE"), index=True
    )
