from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CursoBloque(Base):
    """Ruta de aprendizaje propia de un curso: que bloques y en que orden."""

    __tablename__ = "curso_bloques"
    __table_args__ = (
        UniqueConstraint("curso_id", "orden"),
        CheckConstraint("orden > 0", name="orden"),
    )

    curso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cursos.id", ondelete="CASCADE"), primary_key=True
    )
    bloque_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bloques.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    orden: Mapped[int] = mapped_column(Integer)
