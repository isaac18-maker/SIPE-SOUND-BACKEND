from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ESTADOS_EVALUACION
from app.core.longitudes import (
    APROBACION_MAX,
    APROBACION_MIN,
    DESCRIPCION_MAX,
    ENUNCIADO_MAX,
    ENUNCIADO_MIN,
    INTENTOS_MAX_MAX,
    INTENTOS_MAX_MIN,
    OPCION_MAX,
    OPCIONES_MAX,
    OPCIONES_MIN,
    TITULO_MAX,
    TITULO_MIN,
)
from app.models.base import Base, en_lista, entero_entre, largo_entre, largo_maximo


class Evaluacion(Base):
    """Evaluacion de un bloque (global, curso_id nulo) o de un curso (HU-B-308)."""

    __tablename__ = "evaluaciones"
    __table_args__ = (
        CheckConstraint("num_nonnulls(bloque_id, curso_id) >= 1", name="bloque_o_curso"),
        CheckConstraint(en_lista("estado", ESTADOS_EVALUACION), name="estado"),
        CheckConstraint(largo_entre("titulo", TITULO_MIN, TITULO_MAX), name="titulo"),
        CheckConstraint(largo_maximo("descripcion", DESCRIPCION_MAX), name="descripcion"),
        CheckConstraint(
            entero_entre("porcentaje_aprobacion", APROBACION_MIN, APROBACION_MAX),
            name="porcentaje_aprobacion",
        ),
        CheckConstraint(
            entero_entre("intentos_max", INTENTOS_MAX_MIN, INTENTOS_MAX_MAX), name="intentos_max"
        ),
        # Una sola evaluacion global vigente por bloque: es la que desbloquea el siguiente.
        Index(
            "uq_evaluaciones_bloque_global",
            "bloque_id",
            unique=True,
            postgresql_where=text("curso_id IS NULL AND estado <> 'cerrada'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str | None] = mapped_column(Text)
    bloque_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bloques.id", ondelete="CASCADE"), index=True
    )
    curso_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cursos.id", ondelete="CASCADE"), index=True
    )
    autor_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    porcentaje_aprobacion: Mapped[int] = mapped_column(Integer, server_default=text("80"))
    intentos_max: Mapped[int | None] = mapped_column(Integer)
    fecha_limite: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(Text, server_default="borrador")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PreguntaEvaluacion(Base):
    """Pregunta de opcion unica. `opciones` es un arreglo JSON de textos."""

    __tablename__ = "preguntas_evaluacion"
    __table_args__ = (
        UniqueConstraint("evaluacion_id", "orden"),
        CheckConstraint("orden > 0", name="orden"),
        CheckConstraint(largo_entre("enunciado", ENUNCIADO_MIN, ENUNCIADO_MAX), name="enunciado"),
        CheckConstraint(
            f"public.opciones_validas(opciones, {OPCIONES_MIN}, {OPCIONES_MAX}, {OPCION_MAX})",
            name="opciones",
        ),
        CheckConstraint(
            "respuesta_correcta >= 0 AND respuesta_correcta < jsonb_array_length(opciones)",
            name="respuesta_en_rango",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluacion_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluaciones.id", ondelete="CASCADE"), index=True
    )
    enunciado: Mapped[str] = mapped_column(Text)
    opciones: Mapped[list[str]] = mapped_column(JSONB)
    respuesta_correcta: Mapped[int] = mapped_column(Integer)
    orden: Mapped[int] = mapped_column(Integer)


class IntentoEvaluacion(Base):
    """Cada intento queda registrado; el mejor puntaje se calcula, no se guarda."""

    __tablename__ = "intentos_evaluacion"
    __table_args__ = (
        Index("ix_intentos_evaluacion_evaluacion_estudiante", "evaluacion_id", "estudiante_id"),
        CheckConstraint("puntaje >= 0 AND puntaje <= 100", name="puntaje"),
        CheckConstraint("total > 0 AND correctas >= 0 AND correctas <= total", name="conteo"),
        CheckConstraint("jsonb_typeof(respuestas) = 'object'", name="respuestas"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    evaluacion_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluaciones.id", ondelete="CASCADE")
    )
    estudiante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    puntaje: Mapped[int] = mapped_column(Integer)
    correctas: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    aprobado: Mapped[bool] = mapped_column(Boolean)
    # {"<id de pregunta>": <indice elegido>}
    respuestas: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
