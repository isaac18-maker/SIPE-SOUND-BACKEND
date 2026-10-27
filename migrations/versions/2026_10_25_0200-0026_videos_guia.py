"""video guia de YouTube en bloques, lecciones, ejercicios y acordes

HU: HU-B-410
Revision ID: 0026
Revises: 0025
Create Date: 2026-10-25 02:00:00+00:00
Tipo: esquema
Destructiva: no

Un video OPCIONAL por contenido. Se guarda solo el id de YouTube (11 caracteres) y, si se
quiere, el segundo de inicio: nunca la URL completa. Columnas nulas, asi que el contenido que
ya existe no cambia.
CHECK en cada tabla: id con 11 caracteres validos, inicio entre 0 y 43200 (12 h), y no hay
segundo de inicio sin video.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | Sequence[str] | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("bloques", "lecciones", "ejercicios", "acordes")


def upgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("video_youtube_id", sa.Text(), nullable=True))
        op.add_column(tabla, sa.Column("video_inicio_seg", sa.Integer(), nullable=True))
        op.create_check_constraint(
            op.f(f"ck_{tabla}_video_youtube_id"),
            tabla,
            "video_youtube_id IS NULL OR video_youtube_id ~ '^[A-Za-z0-9_-]{11}$'",
        )
        op.create_check_constraint(
            op.f(f"ck_{tabla}_video_inicio_seg"),
            tabla,
            "video_inicio_seg IS NULL OR (video_inicio_seg >= 0 AND video_inicio_seg <= 43200)",
        )
        op.create_check_constraint(
            op.f(f"ck_{tabla}_video_inicio_con_video"),
            tabla,
            "video_inicio_seg IS NULL OR video_youtube_id IS NOT NULL",
        )


def downgrade() -> None:
    for tabla in reversed(TABLAS):
        op.drop_constraint(op.f(f"ck_{tabla}_video_inicio_con_video"), tabla, type_="check")
        op.drop_constraint(op.f(f"ck_{tabla}_video_inicio_seg"), tabla, type_="check")
        op.drop_constraint(op.f(f"ck_{tabla}_video_youtube_id"), tabla, type_="check")
        op.drop_column(tabla, "video_inicio_seg")
        op.drop_column(tabla, "video_youtube_id")
