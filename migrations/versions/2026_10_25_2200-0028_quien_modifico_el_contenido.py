"""quien modifico por ultima vez lecciones, ejercicios y evaluaciones

HU: HU-B-412
Revision ID: 0028
Revises: 0027
Create Date: 2026-10-25 22:00:00+00:00
Tipo: esquema
Destructiva: no

- lecciones, ejercicios y evaluaciones: actualizado_por (-> profiles, SET NULL, con indice). Nulo
  = nadie lo ha modificado desde que se creo (el autor ya esta en autor_id). Lo llena el servicio
  en cada edicion, cambio de estado o reemplazo de preguntas; el docente de un curso puede editar
  y publicar contenido del administrador y asi se sabe quien lo toco.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | Sequence[str] | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("lecciones", "ejercicios", "evaluaciones")


def upgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("actualizado_por", postgresql.UUID(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{tabla}_actualizado_por_profiles"),
            tabla,
            "profiles",
            ["actualizado_por"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(op.f(f"ix_{tabla}_actualizado_por"), tabla, ["actualizado_por"])


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_index(op.f(f"ix_{tabla}_actualizado_por"), table_name=tabla)
        op.drop_constraint(op.f(f"fk_{tabla}_actualizado_por_profiles"), tabla, type_="foreignkey")
        op.drop_column(tabla, "actualizado_por")
