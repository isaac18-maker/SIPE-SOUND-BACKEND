"""cursos sin docente: un curso puede quedar disponible para que un docente se asigne

HU: HU-B-413
Revision ID: 0029
Revises: 0028
Create Date: 2026-10-26 01:00:00+00:00
Tipo: esquema
Destructiva: no

- cursos.docente_id admite NULL: el administrador crea cursos sin docente y un docente se asigna
  (o se retira) desde su panel. La FK sigue en RESTRICT: un docente con cursos no se elimina hasta
  reasignarlos. Nulo = "curso disponible". Las inscripciones de un curso sin docente se conservan.
- El downgrade solo es posible si ningun curso esta sin docente (de lo contrario fallaria el
  NOT NULL: primero hay que asignarlos).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | Sequence[str] | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("cursos", "docente_id", nullable=True)


def downgrade() -> None:
    op.alter_column("cursos", "docente_id", nullable=False)
