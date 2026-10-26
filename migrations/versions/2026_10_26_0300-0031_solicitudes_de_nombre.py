"""solicitudes de cambio de nombre como solicitudes pendientes de aceptacion

HU: HU-B-415
Revision ID: 0031
Revises: 0030
Create Date: 2026-10-26 03:00:00+00:00
Tipo: esquema
Destructiva: no

- solicitudes_nombre: un estudiante o docente pide que un administrador habilite el cambio de su
  nombre y el admin la acepta (activa profiles.puede_editar_nombre) o la rechaza. CASCADE con la
  cuenta; quien la resolvio queda como SET NULL (contrato de BD, secc. 4).
- Una sola solicitud PENDIENTE por persona (indice unico parcial); las resueltas son historial.
- Coherencia: pendiente <=> sin fecha de resolucion. RLS activo y sin politicas: solo el backend.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: str | Sequence[str] | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "solicitudes_nombre"


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), server_default="pendiente", nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resuelta_por", postgresql.UUID(as_uuid=False), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["profiles.id"],
            name=op.f(f"fk_{TABLA}_usuario_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resuelta_por"],
            ["profiles.id"],
            name=op.f(f"fk_{TABLA}_resuelta_por_profiles"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "estado in ('pendiente', 'aceptada', 'rechazada')", name=op.f(f"ck_{TABLA}_estado")
        ),
        sa.CheckConstraint(
            "char_length(btrim(mensaje)) between 1 and 1000", name=op.f(f"ck_{TABLA}_mensaje")
        ),
        sa.CheckConstraint(
            "(estado = 'pendiente') = (resuelta_en is null)",
            name=op.f(f"ck_{TABLA}_resolucion_coherente"),
        ),
    )
    op.create_index(op.f(f"ix_{TABLA}_usuario_id"), TABLA, ["usuario_id"])
    op.create_index(op.f(f"ix_{TABLA}_resuelta_por"), TABLA, ["resuelta_por"])
    op.create_index(
        op.f(f"uq_{TABLA}_pendiente"),
        TABLA,
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'pendiente'"),
    )
    op.execute(f"alter table public.{TABLA} enable row level security")


def downgrade() -> None:
    op.drop_table(TABLA)
