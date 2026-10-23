from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class _AvanceMixin:
    """Columnas comunes del progreso de un estudiante sobre un contenido."""

    porcentaje: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    completado: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProgresoLeccion(_AvanceMixin, Base):
    __tablename__ = "progreso_lecciones"
    __table_args__ = (
        CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
        Index("ix_progreso_lecciones_leccion_id", "leccion_id"),
    )

    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    leccion_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lecciones.id", ondelete="CASCADE"), primary_key=True
    )


class ProgresoEjercicio(_AvanceMixin, Base):
    __tablename__ = "progreso_ejercicios"
    __table_args__ = (
        CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
        CheckConstraint(
            "mejor_bpm IS NULL OR (mejor_bpm >= 20 AND mejor_bpm <= 300)", name="mejor_bpm"
        ),
        Index("ix_progreso_ejercicios_ejercicio_id", "ejercicio_id"),
    )

    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    ejercicio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ejercicios.id", ondelete="CASCADE"), primary_key=True
    )
    mejor_bpm: Mapped[int | None] = mapped_column(Integer)
