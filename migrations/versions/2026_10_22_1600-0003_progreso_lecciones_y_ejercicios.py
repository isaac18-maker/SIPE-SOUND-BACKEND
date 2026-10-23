"""progreso_lecciones y progreso_ejercicios con claves foraneas

HU: HU-B-305
Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22 16:00:00+00:00
Tipo: esquema
Destructiva: no

Reemplaza la tabla polimorfica `progreso` (tipo + contenido_id, sin FK) para
lecciones y ejercicios. Con FK reales el borrado en cascada es posible:
  profiles  -> progreso_*  ON DELETE CASCADE (supresion de datos del estudiante)
  lecciones -> progreso_lecciones  ON DELETE CASCADE
  ejercicios -> progreso_ejercicios ON DELETE CASCADE
La tabla `progreso` NO se toca: conserva el progreso de bloques hasta HU-B-308.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("progreso_lecciones", "progreso_ejercicios")


def _columnas_comunes() -> list[sa.Column]:
    return [
        sa.Column("porcentaje", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def _crear(tabla: str, columna: str, referencia: str, extra: list[sa.Column]) -> None:
    op.create_table(
        tabla,
        sa.Column("estudiante_id", postgresql.UUID(), nullable=False),
        sa.Column(columna, sa.Integer(), nullable=False),
        *_columnas_comunes(),
        *extra,
        sa.PrimaryKeyConstraint("estudiante_id", columna, name=op.f(f"pk_{tabla}")),
        sa.ForeignKeyConstraint(
            ["estudiante_id"],
            ["profiles.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{tabla}_estudiante_id_profiles"),
        ),
        sa.ForeignKeyConstraint(
            [columna],
            [f"{referencia}.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{tabla}_{columna}_{referencia}"),
        ),
        sa.CheckConstraint(
            "porcentaje >= 0 AND porcentaje <= 100", name=op.f(f"ck_{tabla}_porcentaje")
        ),
    )
    # La PK cubre estudiante_id; la FK al contenido necesita su propio indice.
    op.create_index(op.f(f"ix_{tabla}_{columna}"), tabla, [columna])
    op.execute(
        f"create trigger {tabla}_tocar_actualizado_en before update on public.{tabla} "
        "for each row execute function public.tocar_actualizado_en()"
    )
    # Defensa en profundidad: el backend usa su propia conexion, pero si alguien
    # consulta con la anon key solo ve y escribe su propio progreso.
    op.execute(f"alter table public.{tabla} enable row level security")
    for comando, condicion in (
        ("select", "using"),
        ("insert", "with check"),
        ("update", "using"),
    ):
        op.execute(
            f'create policy "Propio progreso ({comando})" on public.{tabla} '
            f"for {comando} {condicion} (auth.uid() = estudiante_id)"
        )


def upgrade() -> None:
    _crear("progreso_lecciones", "leccion_id", "lecciones", [])
    _crear(
        "progreso_ejercicios",
        "ejercicio_id",
        "ejercicios",
        [sa.Column("mejor_bpm", sa.Integer(), nullable=True)],
    )
    op.create_check_constraint(
        op.f("ck_progreso_ejercicios_mejor_bpm"),
        "progreso_ejercicios",
        "mejor_bpm IS NULL OR (mejor_bpm >= 20 AND mejor_bpm <= 300)",
    )


def downgrade() -> None:
    for tabla in reversed(TABLAS):
        op.drop_table(tabla)
