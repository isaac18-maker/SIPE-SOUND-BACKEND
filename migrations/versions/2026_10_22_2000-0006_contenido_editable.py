"""contenido editable: estado, autoria, auditoria y cascada bloques -> lecciones

HU: HU-B-306
Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22 20:00:00+00:00
Tipo: esquema
Destructiva: si (solo se reemplaza una FK; no se borran datos)

- bloques, lecciones, ejercicios: estado (borrador | publicado | archivado), por
  defecto 'publicado' para que el contenido existente siga visible.
- lecciones y ejercicios: autor_id (-> profiles, SET NULL), archivado_en, duracion_min.
- actualizado_en en las tres tablas, mantenido por tocar_actualizado_en().
- lecciones.bloque_id: ON DELETE SET NULL -> CASCADE (contrato de BD, seccion 4).
- Indices en todas las FK; bloques.orden_index unico.
La columna de texto `duracion` se conserva hasta HU-B-312.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ESTADOS = "estado = ANY (ARRAY['borrador'::text, 'publicado'::text, 'archivado'::text])"
TABLAS = ("bloques", "lecciones", "ejercicios")
CON_AUTORIA = ("lecciones", "ejercicios")


def _agregar_estado_y_auditoria(tabla: str) -> None:
    op.add_column(
        tabla,
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'publicado'::text")),
    )
    op.create_check_constraint(op.f(f"ck_{tabla}_estado"), tabla, ESTADOS)
    op.add_column(
        tabla,
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        f"create trigger {tabla}_tocar_actualizado_en before update on public.{tabla} "
        "for each row execute function public.tocar_actualizado_en()"
    )


def _agregar_autoria(tabla: str) -> None:
    op.add_column(tabla, sa.Column("autor_id", postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        op.f(f"fk_{tabla}_autor_id_profiles"),
        tabla,
        "profiles",
        ["autor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f(f"ix_{tabla}_autor_id"), tabla, ["autor_id"])
    op.add_column(tabla, sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True))
    # Coherencia: archivado <=> tiene fecha de archivo.
    op.create_check_constraint(
        op.f(f"ck_{tabla}_archivado_coherente"),
        tabla,
        "(estado = 'archivado') = (archivado_en IS NOT NULL)",
    )
    op.add_column(tabla, sa.Column("duracion_min", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f(f"ck_{tabla}_duracion_min"), tabla, "duracion_min IS NULL OR duracion_min > 0"
    )


def upgrade() -> None:
    for tabla in TABLAS:
        _agregar_estado_y_auditoria(tabla)
    for tabla in CON_AUTORIA:
        _agregar_autoria(tabla)

    op.create_unique_constraint(op.f("uq_bloques_orden_index"), "bloques", ["orden_index"])

    # Una leccion pertenece a su bloque: si se borra el bloque, se borran sus lecciones.
    op.drop_constraint(  # destructivo-aprobado: HU-B-306 (se reemplaza la FK, sin perder datos)
        "lecciones_bloque_id_fkey", "lecciones", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_lecciones_bloque_id_bloques"),
        "lecciones",
        "bloques",
        ["bloque_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_lecciones_bloque_id"), "lecciones", ["bloque_id"])
    op.create_index(op.f("ix_ejercicios_leccion_id"), "ejercicios", ["leccion_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ejercicios_leccion_id"), table_name="ejercicios")
    op.drop_index(op.f("ix_lecciones_bloque_id"), table_name="lecciones")
    op.drop_constraint(op.f("fk_lecciones_bloque_id_bloques"), "lecciones", type_="foreignkey")
    op.create_foreign_key(
        op.f("lecciones_bloque_id_fkey"),
        "lecciones",
        "bloques",
        ["bloque_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(op.f("uq_bloques_orden_index"), "bloques", type_="unique")
    for tabla in CON_AUTORIA:
        for restriccion in ("duracion_min", "archivado_coherente"):
            op.drop_constraint(op.f(f"ck_{tabla}_{restriccion}"), tabla, type_="check")
        op.drop_column(tabla, "duracion_min")
        op.drop_column(tabla, "archivado_en")
        op.drop_index(op.f(f"ix_{tabla}_autor_id"), table_name=tabla)
        op.drop_constraint(op.f(f"fk_{tabla}_autor_id_profiles"), tabla, type_="foreignkey")
        op.drop_column(tabla, "autor_id")
    for tabla in TABLAS:
        op.execute(f"drop trigger if exists {tabla}_tocar_actualizado_en on public.{tabla}")
        op.drop_column(tabla, "actualizado_en")
        op.drop_constraint(op.f(f"ck_{tabla}_estado"), tabla, type_="check")
        op.drop_column(tabla, "estado")
