from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ALCANCES_MENSAJE
from app.core.longitudes import ASUNTO_MAX, ASUNTO_MIN, CUERPO_MENSAJE_MAX, CUERPO_MENSAJE_MIN
from app.models.base import Base, en_lista, largo_entre


class Mensaje(Base):
    """Mensaje interno (HU-B-409). Nunca se envia por correo."""

    __tablename__ = "mensajes"
    __table_args__ = (
        CheckConstraint(largo_entre("asunto", ASUNTO_MIN, ASUNTO_MAX), name="asunto"),
        CheckConstraint(
            largo_entre("cuerpo", CUERPO_MENSAJE_MIN, CUERPO_MENSAJE_MAX), name="cuerpo"
        ),
        CheckConstraint(en_lista("alcance", ALCANCES_MENSAJE), name="alcance"),
        # Un curso puede borrarse (SET NULL): solo se exige "curso_id => alcance curso".
        CheckConstraint(
            "curso_id IS NULL OR alcance = 'curso'", name="curso_solo_con_alcance_curso"
        ),
        Index("ix_mensajes_hilo_creado", "hilo_id", "creado_en"),
        Index("ix_mensajes_remitente_creado", "remitente_id", "creado_en"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    # SET NULL: si la persona se elimina, sus mensajes siguen siendo utiles a quien los recibio.
    remitente_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    asunto: Mapped[str] = mapped_column(Text)
    cuerpo: Mapped[str] = mapped_column(Text)
    alcance: Mapped[str] = mapped_column(Text)
    curso_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cursos.id", ondelete="SET NULL"), index=True
    )
    respuesta_a_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("mensajes.id", ondelete="SET NULL"), index=True
    )
    # El id del primer mensaje del hilo (el primero tiene hilo_id = id).
    hilo_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MensajeDestinatario(Base):
    """Quien recibe cada mensaje (y el remitente, ya leido, para ver su propio hilo)."""

    __tablename__ = "mensaje_destinatarios"
    __table_args__ = (
        PrimaryKeyConstraint("mensaje_id", "destinatario_id"),
        Index("ix_mensaje_destinatarios_bandeja", "destinatario_id", "leido_en", "mensaje_id"),
    )

    mensaje_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("mensajes.id", ondelete="CASCADE")
    )
    destinatario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="CASCADE")
    )
    leido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
