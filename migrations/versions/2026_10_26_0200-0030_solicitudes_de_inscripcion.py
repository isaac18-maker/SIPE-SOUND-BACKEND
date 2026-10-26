"""solicitudes de inscripcion a cursos

HU: HU-B-414
Revision ID: 0030
Revises: 0029
Create Date: 2026-10-26 02:00:00+00:00
Tipo: esquema
Destructiva: no

- solicitudes_inscripcion: un estudiante pide entrar a un curso y el docente del curso (o un
  administrador) la acepta o la rechaza. Al aceptarla se crea la inscripcion. CASCADE con el curso
  y con la cuenta del estudiante; quien la resolvio queda como SET NULL (contrato de BD, secc. 4).
- Una sola solicitud PENDIENTE por (curso, estudiante): indice unico parcial. Las resueltas se
  conservan como historial y el estudiante puede volver a pedir tras un rechazo.
- Coherencia: pendiente <=> sin fecha de resolucion. RLS activo y sin politicas: solo el backend.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str | Sequence[str] | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "solicitudes_inscripcion"


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("curso_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("estado", sa.Text(), server_default="pendiente", nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resuelta_por", postgresql.UUID(as_uuid=False), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["curso_id"],
            ["cursos.id"],
            name=op.f(f"fk_{TABLA}_curso_id_cursos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"],
            ["profiles.id"],
            name=op.f(f"fk_{TABLA}_estudiante_id_profiles"),
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
            "(estado = 'pendiente') = (resuelta_en is null)",
            name=op.f(f"ck_{TABLA}_resolucion_coherente"),
        ),
    )
    op.create_index(op.f(f"ix_{TABLA}_curso_id"), TABLA, ["curso_id"])
    op.create_index(op.f(f"ix_{TABLA}_estudiante_id"), TABLA, ["estudiante_id"])
    op.create_index(op.f(f"ix_{TABLA}_resuelta_por"), TABLA, ["resuelta_por"])
    op.create_index(
        op.f(f"uq_{TABLA}_pendiente"),
        TABLA,
        ["curso_id", "estudiante_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'pendiente'"),
    )
    op.execute(f"alter table public.{TABLA} enable row level security")


def downgrade() -> None:
    op.drop_table(TABLA)
