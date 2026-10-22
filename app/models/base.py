# =========================================================
# Base declarativa. La convencion de nombres del contrato de BD se
# aplica a toda restriccion NUEVA. Las tablas heredadas conservan sus
# nombres reales con existente(), para que Alembic no detecte cambios.
# =========================================================
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql.elements import conv

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

NIVELES = ("principiante", "intermedio", "avanzado")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def existente(nombre: str) -> conv:
    """Nombre real de una restriccion heredada (no se reescribe con la convencion)."""
    return conv(nombre)


def en_lista(columna: str, valores: tuple[str, ...]) -> str:
    """Expresion CHECK equivalente a la de la base: columna in (...)."""
    return f"{columna} in ({', '.join(repr(v) for v in valores)})"


class CreadoEnMixin:
    creado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Tabla de Supabase Auth: solo se declara para poder referenciarla con FK.
# Alembic la EXCLUYE (protecciones del contrato de BD, HU-B-302).
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    schema="auth",
)


class EstadoMixin:
    """Ciclo de vida del contenido: borrador -> publicado -> archivado (HU-B-306)."""

    estado: Mapped[str] = mapped_column(Text, server_default="publicado")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AutoriaMixin:
    """Contenido creado por un docente; sobrevive a su autor (SET NULL)."""

    @declared_attr
    def autor_id(cls) -> Mapped[str | None]:  # noqa: N805 - declared_attr recibe la clase
        return mapped_column(
            UUID(as_uuid=False), ForeignKey("profiles.id", ondelete="SET NULL"), index=True
        )

    archivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duracion_min: Mapped[int | None] = mapped_column(Integer)
