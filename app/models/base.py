# =========================================================
# Base declarativa. La convencion de nombres del contrato de BD se
# aplica a toda restriccion NUEVA. Las tablas heredadas conservan sus
# nombres reales con existente(), para que Alembic no detecte cambios.
# =========================================================
from datetime import datetime

from sqlalchemy import Column, DateTime, MetaData, Table, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
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
