"""actividad del docente en la plataforma

HU: HU-B-418
Revision ID: 0034
Revises: 0033
Create Date: 2026-10-27 03:00:00+00:00
Tipo: esquema
Destructiva: no

- actividad_docente: que tipo de cosa hizo un docente y en que curso (nunca el contenido).
  docente_id: profiles CASCADE; curso_id: cursos SET NULL (contrato de BD, seccion 4).
  Indices (docente_id, creado_en desc) y (curso_id, creado_en desc). RLS activo y sin
  politicas: solo el backend, como envios_correo. Se conserva 180 dias (limpieza por lotes).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034"
down_revision: str | Sequence[str] | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "actividad_docente"
TIPOS = (
    "sesion",
    "leccion",
    "ejercicio",
    "evaluacion",
    "retroalimentacion",
    "mensaje",
    "curso",
)
ACCIONES = (
    "inicio",
    "creo",
    "edito",
    "publico",
    "archivo",
    "elimino",
    "comento",
    "envio",
    "retiro_estudiante",
    "regenero_codigo",
    "definio_ruta",
)


def _lista(valores: Sequence[str]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _ck(nombre: str, expresion: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{TABLA}_{nombre}"))


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("docente_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("curso_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["docente_id"],
            ["profiles.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{TABLA}_docente_id_profiles"),
        ),
        sa.ForeignKeyConstraint(
            ["curso_id"],
            ["cursos.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{TABLA}_curso_id_cursos"),
        ),
        _ck("tipo", f"tipo in ({_lista(TIPOS)})"),
        _ck("accion", f"accion in ({_lista(ACCIONES)})"),
    )
    op.create_index(
        "ix_actividad_docente_docente_creado", TABLA, ["docente_id", sa.text("creado_en DESC")]
    )
    op.create_index(
        "ix_actividad_docente_curso_creado", TABLA, ["curso_id", sa.text("creado_en DESC")]
    )
    op.execute(f"alter table public.{TABLA} enable row level security")


def downgrade() -> None:
    op.drop_table(TABLA)  # destructivo-aprobado: HU-B-418
