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


class Leccion(CreadoEnMixin, Base):
    __tablename__ = "lecciones"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("lecciones_pkey")),
        # Hoy SET NULL; el contrato pide CASCADE (HU-B-306).
        ForeignKeyConstraint(
            ["bloque_id"],
            ["bloques.id"],
            ondelete="SET NULL",
            name=existente("lecciones_bloque_id_fkey"),
        ),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("lecciones_nivel_check")),
    )

    id: Mapped[int] = mapped_column(Integer)
    numero: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    duracion: Mapped[str | None] = mapped_column(Text)
    acordes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    temas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    contenido: Mapped[str | None] = mapped_column(Text)
    bloque_id: Mapped[int | None] = mapped_column(Integer)
