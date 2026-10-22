"""poblar duracion_min desde el texto de duracion

HU: HU-B-306
Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22 20:10:00+00:00
Tipo: datos
Destructiva: no

"30 min" -> 30. Solo se llenan filas cuyo texto contiene un numero y que aun no
tienen duracion_min (idempotente). El texto original no se modifica.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POBLAR = (
    "update public.lecciones set duracion_min = (regexp_match(duracion, '(\\d+)'))[1]::int "
    "where duracion_min is null and duracion ~ '\\d'",
    "update public.ejercicios set duracion_min = (regexp_match(duracion, '(\\d+)'))[1]::int "
    "where duracion_min is null and duracion ~ '\\d'",
)
VACIAR = (
    "update public.lecciones set duracion_min = null",
    "update public.ejercicios set duracion_min = null",
)


def upgrade() -> None:
    for sentencia in POBLAR:
        op.execute(sentencia)


def downgrade() -> None:
    for sentencia in VACIAR:
        op.execute(sentencia)
