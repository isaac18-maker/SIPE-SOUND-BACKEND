"""retirar la tabla partituras (sin uso)

HU: HU-B-314
Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22 21:00:00+00:00
Tipo: esquema
Destructiva: si

Ningun endpoint ni el frontend usa `partituras`, ninguna FK la referencia y tiene
0 filas (verificado el 2026-10-22). Guardia: si al aplicar tiene filas, aborta sin
borrar nada. downgrade() la recrea con su definicion original (vacia).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GUARDIA_TABLA_VACIA = """
do $$
begin
  if exists (select 1 from public.partituras) then
    raise exception 'partituras tiene datos: respaldalos o migralos antes de retirar la tabla';
  end if;
end $$
"""
NIVELES = "nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])"


def upgrade() -> None:
    op.execute(GUARDIA_TABLA_VACIA)
    op.drop_table("partituras")  # destructivo-aprobado: HU-B-314 (tabla vacia y sin uso)


def downgrade() -> None:
    op.create_table(
        "partituras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("artista", sa.Text()),
        sa.Column("nivel", sa.Text(), server_default=sa.text("'principiante'::text")),
        sa.Column("tipo", sa.Text()),
        sa.Column("acordes", postgresql.ARRAY(sa.Text())),
        sa.Column("imagen_url", sa.Text()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("partituras_pkey")),
        sa.CheckConstraint(NIVELES, name=op.f("partituras_nivel_check")),
        sa.CheckConstraint(
            "tipo = ANY (ARRAY['partitura'::text, 'tablatura'::text, 'ambas'::text])",
            name=op.f("partituras_tipo_check"),
        ),
    )
    op.execute("alter table public.partituras enable row level security")
    op.execute(
        'create policy "Lectura pública partituras" on public.partituras for select using (true)'
    )
