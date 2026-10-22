from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente


class Ejercicio(CreadoEnMixin, Base):
    __tablename__ = "ejercicios"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("ejercicios_pkey")),
        ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            ondelete="SET NULL",
            name=existente("ejercicios_leccion_id_fkey"),
        ),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("ejercicios_nivel_check")),
    )

    id: Mapped[int] = mapped_column(Integer)
    leccion_id: Mapped[int | None] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    bpm_recomendado: Mapped[int | None] = mapped_column(Integer, server_default="60")
    duracion: Mapped[str | None] = mapped_column(Text)
    compas: Mapped[str | None] = mapped_column(Text, server_default="4/4")
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    pasos: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
