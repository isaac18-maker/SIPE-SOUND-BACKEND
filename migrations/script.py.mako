"""${message}

HU: HU-B-XXX
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
Tipo: esquema
Destructiva: no

Completar antes del commit (scripts/check_migrations.py lo valida):
- HU: identificador real de la historia.
- Tipo: "esquema" o "datos" (nunca ambos en la misma revision).
- Destructiva: "si" exige marcar cada operacion con "# destructivo-aprobado: HU-B-XXX".
- downgrade() debe revertir el upgrade (o lanzar NotImplementedError con el motivo).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
