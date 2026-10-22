"""profiles rol y actualizado_en

HU: HU-B-304
Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 14:00:00+00:00
Tipo: esquema
Destructiva: no

- profiles.rol (estudiante | docente | admin), por defecto 'estudiante'.
- profiles.actualizado_en mantenido por el trigger generico tocar_actualizado_en().
- Un usuario autenticado solo puede editar nombre y nivel de su perfil: el rol
  NUNCA se puede cambiar desde el cliente con la anon key (privilegio por columna).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES_CLIENTE = "anon, authenticated"

FUNCION_TOCAR_ACTUALIZADO_EN = """
create or replace function public.tocar_actualizado_en()
returns trigger
language plpgsql
as $function$
begin
  new.actualizado_en = now();
  return new;
end;
$function$
"""


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("rol", sa.Text(), nullable=False, server_default=sa.text("'estudiante'::text")),
    )
    op.create_check_constraint(
        op.f("ck_profiles_rol"),
        "profiles",
        "rol = ANY (ARRAY['estudiante'::text, 'docente'::text, 'admin'::text])",
    )
    op.add_column(
        "profiles",
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(FUNCION_TOCAR_ACTUALIZADO_EN)
    op.execute(
        "create trigger profiles_tocar_actualizado_en before update on public.profiles "
        "for each row execute function public.tocar_actualizado_en()"
    )
    # Privilegio por columna: la politica RLS "Editar propio perfil" permite el UPDATE
    # de la fila; sin esto, un estudiante podria cambiar su propio rol.
    op.execute(f"revoke update on public.profiles from {ROLES_CLIENTE}")
    op.execute(f"grant update (nombre, nivel) on public.profiles to {ROLES_CLIENTE}")


def downgrade() -> None:
    op.execute(f"revoke update (nombre, nivel) on public.profiles from {ROLES_CLIENTE}")
    op.execute(f"grant update on public.profiles to {ROLES_CLIENTE}")
    op.execute("drop trigger if exists profiles_tocar_actualizado_en on public.profiles")
    op.execute("drop function if exists public.tocar_actualizado_en()")
    op.drop_column("profiles", "actualizado_en")
    op.drop_constraint(op.f("ck_profiles_rol"), "profiles", type_="check")
    op.drop_column("profiles", "rol")
