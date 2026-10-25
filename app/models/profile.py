from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ROLES
from app.core.longitudes import (
    APELLIDO_PERSONA_MAX,
    APELLIDO_PERSONA_MIN,
    NOMBRE_PERSONA_MAX,
    NOMBRE_PERSONA_MIN,
)
from app.models.base import NIVELES, Base, CreadoEnMixin, en_lista, existente, largo_entre

APELLIDO_LARGO = largo_entre("apellido", APELLIDO_PERSONA_MIN, APELLIDO_PERSONA_MAX)


class Profile(CreadoEnMixin, Base):
    """Lo crea el trigger on_auth_user_created al registrarse un usuario."""

    __tablename__ = "profiles"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=existente("profiles_pkey")),
        ForeignKeyConstraint(
            ["id"], ["auth.users.id"], ondelete="CASCADE", name=existente("profiles_id_fkey")
        ),
        CheckConstraint(en_lista("nivel", NIVELES), name=existente("profiles_nivel_check")),
        CheckConstraint(en_lista("rol", ROLES), name="rol"),
        CheckConstraint(
            largo_entre("nombre", NOMBRE_PERSONA_MIN, NOMBRE_PERSONA_MAX), name="nombre"
        ),
        # Sin caracteres de control (saltos de linea, tabuladores, NUL...).
        CheckConstraint("nombre !~ '[[:cntrl:]]'", name="nombre_sin_control"),
        # El apellido es opcional en la base: las cuentas anteriores a HU-B-407 no lo tienen.
        CheckConstraint(f"apellido IS NULL OR {APELLIDO_LARGO}", name="apellido"),
        CheckConstraint(
            "(suspendido_en IS NULL) = (motivo_suspension IS NULL)", name="suspension_coherente"
        ),
        CheckConstraint(
            "motivo_suspension IS NULL OR char_length(btrim(motivo_suspension)) BETWEEN 10 AND 300",
            name="motivo_suspension",
        ),
        CheckConstraint(
            "apellido IS NULL OR apellido !~ '[[:cntrl:]]'", name="apellido_sin_control"
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    nombre: Mapped[str] = mapped_column(Text)
    apellido: Mapped[str | None] = mapped_column(Text)
    # Lo activa un administrador, persona por persona (HU-B-407).
    puede_editar_nombre: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    nivel: Mapped[str] = mapped_column(Text, server_default="principiante")
    rol: Mapped[str] = mapped_column(Text, server_default="estudiante")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Lo llena el backend al verificar el codigo enviado al correo (HU-B-402). Nulo = la
    # cuenta no puede iniciar sesion ni usar la API.
    correo_verificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Una cuenta suspendida no inicia sesion ni usa la API (HU-B-405).
    suspendido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_suspension: Mapped[str | None] = mapped_column(Text)
