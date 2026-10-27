"""confirmar el correo tambien en Supabase Auth cuando el backend lo verifica

HU: HU-B-419
Revision ID: 0032
Revises: 0031
Create Date: 2026-10-27 01:00:00+00:00
Tipo: datos
Destructiva: no

El backend decide quien esta verificado con profiles.correo_verificado_en (HU-B-402), pero
Supabase Auth rechaza el inicio de sesion (email_not_confirmed) mientras
auth.users.email_confirmed_at siga nulo. Las cuentas creadas con "Confirm email" activo y
verificadas despues por codigo quedaban atrapadas.
- confirmar_correo_auth(usuario): SECURITY DEFINER, como fijar_contrasena (0021). Conserva la
  fecha si ya existia. El trigger on_auth_user_confirmed ya no existe (0019): no cambia roles.
- Dato: se repara toda cuenta ya verificada con email_confirmed_at nulo.
Seguridad: se revoca EXECUTE a public, anon y authenticated (Supabase expone public como RPC).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0032"
down_revision: str | Sequence[str] | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCION = "public.confirmar_correo_auth(uuid)"

FUNCION_CONFIRMAR = """
create or replace function public.confirmar_correo_auth(p_usuario uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  update auth.users
     set email_confirmed_at = coalesce(email_confirmed_at, now()),
         updated_at = now()
   where id = p_usuario;
  if not found then
    raise exception 'usuario_inexistente' using errcode = 'P0002';
  end if;
end;
$function$
"""

REPARAR = """
update auth.users u
   set email_confirmed_at = p.correo_verificado_en,
       updated_at = now()
  from public.profiles p
 where p.id = u.id
   and p.correo_verificado_en is not null
   and u.email_confirmed_at is null
"""


def upgrade() -> None:
    op.execute(FUNCION_CONFIRMAR)
    op.execute(f"revoke execute on function {FUNCION} from public, anon, authenticated")
    op.execute(REPARAR)


def downgrade() -> None:
    # El dato reparado se conserva: confirmar un correo ya verificado no es reversible ni dañino.
    op.execute(f"drop function {FUNCION}")
