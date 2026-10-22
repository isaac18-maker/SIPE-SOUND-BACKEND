from sqlalchemy import ARRAY, ForeignKeyConstraint, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreadoEnMixin, existente


class QuizPregunta(CreadoEnMixin, Base):
    """Se migra a preguntas_evaluacion en HU-B-308."""

    __tablename__ = "quiz_preguntas"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("quiz_preguntas_pkey")),
        ForeignKeyConstraint(
            ["bloque_id"],
            ["bloques.id"],
            ondelete="CASCADE",
            name=existente("quiz_preguntas_bloque_id_fkey"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer)
    bloque_id: Mapped[int] = mapped_column(Integer)
    pregunta: Mapped[str] = mapped_column(Text)
    opciones: Mapped[list[str]] = mapped_column(ARRAY(Text))
    respuesta_correcta: Mapped[int] = mapped_column(Integer)
    orden_index: Mapped[int] = mapped_column(Integer)
