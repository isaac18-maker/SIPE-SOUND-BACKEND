"""integridad: leccion siempre en un bloque y respuesta dentro de las opciones

HU: HU-B-316
Revision ID: 0010
Revises: 0009
Create Date: 2026-10-22 23:10:00+00:00
Tipo: esquema
Destructiva: no

R8. Datos verificados en produccion el 2026-10-22: 0 lecciones sin bloque y 0 preguntas
con la respuesta fuera de rango. Si alguna fila incumpliera al aplicar, PostgreSQL
aborta la revision completa sin modificar nada.
- lecciones.bloque_id NOT NULL: una leccion sin bloque queda fuera de la ruta de
  aprendizaje sin aviso (con la FK en CASCADE desde HU-B-306).
- quiz_preguntas: respuesta_correcta debe ser un indice valido de `opciones`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("lecciones", "bloque_id", existing_type=sa.Integer(), nullable=False)
    op.create_check_constraint(
        op.f("ck_quiz_preguntas_respuesta_en_rango"),
        "quiz_preguntas",
        "respuesta_correcta >= 0 AND respuesta_correcta < cardinality(opciones)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_quiz_preguntas_respuesta_en_rango"), "quiz_preguntas", type_="check"
    )
    op.alter_column("lecciones", "bloque_id", existing_type=sa.Integer(), nullable=True)
