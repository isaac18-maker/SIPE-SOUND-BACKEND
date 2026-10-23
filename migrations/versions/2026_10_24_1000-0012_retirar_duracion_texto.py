"""retirar la columna duracion (texto) de lecciones y ejercicios

HU: HU-B-319
Revision ID: 0012
Revises: 0011
Create Date: 2026-10-24 10:00:00+00:00
Tipo: esquema
Destructiva: si

`duracion` ("20 min") quedo reemplazada por `duracion_min` (entero) en 0007 y la API ya
no la expone. Verificado en produccion el 2026-10-22: toda fila con `duracion` tiene su
`duracion_min`. Guardia: si alguna fila tuviera `duracion` sin `duracion_min`, aborta sin
borrar nada. downgrade() recrea la columna y la rellena desde `duracion_min`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("lecciones", "ejercicios")
RELLENAR = {
    "lecciones": "update public.lecciones set duracion = duracion_min || ' min' "
    "where duracion_min is not null",
    "ejercicios": "update public.ejercicios set duracion = duracion_min || ' min' "
    "where duracion_min is not null",
}

GUARDIA_SIN_PERDIDA = """
do $$
begin
  if exists (select 1 from public.{tabla} where duracion is not null and duracion_min is null) then
    raise exception '{tabla}: hay duracion sin duracion_min; copiala antes de retirar la columna';
  end if;
end $$
"""


def upgrade() -> None:
    for tabla in TABLAS:
        op.execute(GUARDIA_SIN_PERDIDA.format(tabla=tabla))
    op.drop_column("lecciones", "duracion")  # destructivo-aprobado: HU-B-319 (copiada en 0007)
    op.drop_column("ejercicios", "duracion")  # destructivo-aprobado: HU-B-319 (copiada en 0007)


def downgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("duracion", sa.Text(), nullable=True))
        op.execute(RELLENAR[tabla])
