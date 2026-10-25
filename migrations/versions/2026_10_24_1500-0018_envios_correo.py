"""envios_correo: bitacora del resultado de cada correo que sale

HU: HU-B-401
Revision ID: 0018
Revises: 0017
Create Date: 2026-10-24 15:00:00+00:00
Tipo: esquema
Destructiva: no

Guarda solo el tipo, el estado y un codigo corto de error ("smtp_auth", "smtp_timeout"...):
nunca el codigo de verificacion, el enlace, el cuerpo ni el texto del servidor SMTP.
Politica de borrado (contrato de BD, seccion 4): profiles -> envios_correo.usuario_id SET NULL,
la bitacora sobrevive a la cuenta eliminada. El indice (usuario_id, tipo, creado_en) cubre la
FK y la consulta "ultimo envio de este tipo a esta persona". RLS activo y sin politicas:
solo el backend (rol de servidor) lee y escribe.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "envios_correo"
TIPOS = (
    "verificar_correo",
    "reautenticacion",
    "restablecer_contrasena",
    "contrasena_cambiada",
    "cambiar_correo",
    "correo_cambiado",
)


def _ck(nombre: str, expresion: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{TABLA}_{nombre}"))


def upgrade() -> None:
    lista = ", ".join(f"'{tipo}'" for tipo in TIPOS)
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["profiles.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{TABLA}_usuario_id_profiles"),
        ),
        _ck("tipo", f"tipo in ({lista})"),
        _ck("estado", "estado in ('enviado', 'fallido')"),
        _ck("error_formato", "error ~ '^[a-z_]{1,40}$'"),
        _ck("error_coherente", "(estado = 'fallido') = (error IS NOT NULL)"),
    )
    op.create_index(
        "ix_envios_correo_usuario_tipo_creado", TABLA, ["usuario_id", "tipo", "creado_en"]
    )
    op.execute(f"alter table public.{TABLA} enable row level security")


def downgrade() -> None:
    op.drop_table(TABLA)
