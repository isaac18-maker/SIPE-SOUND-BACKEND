"""copiar a correo_verificado_en los correos ya confirmados en Supabase

HU: HU-B-402
Revision ID: 0020
Revises: 0019
Create Date: 2026-10-24 16:10:00+00:00
Tipo: datos
Destructiva: no

Las cuentas confirmadas antes de esta HU siguen entrando sin pedir un codigo. Idempotente:
solo toca perfiles con correo_verificado_en nulo. Al llenar la columna dispara el trigger
on_profile_verificado, que aplica preautorizaciones pendientes de cuentas ya confirmadas
(lo que antes hacia on_auth_user_confirmed).
downgrade(): sin accion. Quitar las fechas dejaria sin acceso a cuentas que ya verificaron;
la revision 0019 elimina la columna entera si se retrocede mas.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | Sequence[str] | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COPIAR = """
update public.profiles p
   set correo_verificado_en = u.email_confirmed_at
  from auth.users u
 where u.id = p.id
   and u.email_confirmed_at is not null
   and p.correo_verificado_en is null
"""


def upgrade() -> None:
    op.execute(COPIAR)


def downgrade() -> None:
    # Sin accion a proposito (ver docstring). 0019 descarta la columna al retroceder.
    op.execute("select 1")
