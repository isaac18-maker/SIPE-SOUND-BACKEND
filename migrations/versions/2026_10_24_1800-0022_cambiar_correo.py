"""funcion para cambiar el correo de una cuenta sin la clave service_role

HU: HU-B-404
Revision ID: 0022
Revises: 0021
Create Date: 2026-10-24 18:00:00+00:00
Tipo: esquema
Destructiva: no

cambiar_correo(usuario, email) es SECURITY DEFINER, como fijar_contrasena (0021):
- Valida formato, largo (254) y que ninguna OTRA cuenta use ese correo (sin distinguir
  mayusculas); si esta en uso lanza 23505, que la API responde 409.
- Actualiza auth.users.email y el correo de su identidad de tipo 'email' (Supabase inicia
  sesion con la identidad), y raw_user_meta_data.email si esa clave existe.
- No toca profiles.correo_verificado_en: el codigo enviado al correo NUEVO ya lo comprobo.
Seguridad: se revoca EXECUTE a public, anon y authenticated; si no, cualquier cliente podria
cambiar el correo de otra persona (y con el, recuperar su cuenta).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | Sequence[str] | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCION = "public.cambiar_correo(uuid, text)"

FUNCION_CAMBIAR = """
create or replace function public.cambiar_correo(p_usuario uuid, p_email text)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_email text := lower(btrim(coalesce(p_email, '')));
begin
  if char_length(v_email) > 254
     or v_email !~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$' then
    raise exception 'correo_invalido' using errcode = '22023';
  end if;
  if exists (
    select 1 from auth.users where lower(email) = v_email and id <> p_usuario
  ) then
    raise exception 'correo_en_uso' using errcode = '23505';
  end if;
  update auth.users
     set email = v_email,
         raw_user_meta_data = case
           when jsonb_exists(coalesce(raw_user_meta_data, '{}'::jsonb), 'email')
             then jsonb_set(raw_user_meta_data, '{email}', to_jsonb(v_email))
           else raw_user_meta_data
         end,
         updated_at = now()
   where id = p_usuario;
  if not found then
    raise exception 'usuario_inexistente' using errcode = 'P0002';
  end if;
  update auth.identities
     set identity_data = jsonb_set(identity_data, '{email}', to_jsonb(v_email)),
         updated_at = now()
   where user_id = p_usuario and provider = 'email';
end;
$function$
"""


def upgrade() -> None:
    op.execute(FUNCION_CAMBIAR)
    op.execute(f"revoke execute on function {FUNCION} from public, anon, authenticated")


def downgrade() -> None:
    op.execute(f"drop function {FUNCION}")
