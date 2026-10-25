"""funciones para fijar la contrasena y cerrar sesiones sin la clave service_role

HU: HU-B-403
Revision ID: 0021
Revises: 0020
Create Date: 2026-10-24 17:00:00+00:00
Tipo: esquema
Destructiva: no   # destructivo-aprobado: HU-B-403 (cerrar_sesiones borra filas de auth.sessions
                  # al ejecutarse, nunca al migrar)

Sin la clave service_role (HU-B-321) el backend no puede cambiar la contrasena por la API de
Supabase. Se hace con funciones SECURITY DEFINER, como aplicar_docente_preautorizado (0014):
- fijar_contrasena(usuario, password): valida 8-72 con letras y numeros y guarda el hash bcrypt
  (costo 10, el formato que usa Supabase Auth) en auth.users.encrypted_password.
- cerrar_sesiones(usuario, excepto): borra las sesiones del usuario (sus refresh tokens caen por
  cascada), salvo la indicada. Los access tokens ya emitidos viven hasta su vencimiento.
Seguridad: Supabase expone las funciones de public como RPC; se revoca EXECUTE a public, anon y
authenticated para que ningun cliente las llame (cualquiera podria cambiar la contrasena ajena).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | Sequence[str] | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCIONES = (
    "public.fijar_contrasena(uuid, text)",
    "public.cerrar_sesiones(uuid, uuid)",
)

FUNCION_FIJAR = """
create or replace function public.fijar_contrasena(p_usuario uuid, p_password text)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if p_password is null
     or char_length(p_password) not between 8 and 72
     or p_password !~ '[A-Za-z]'
     or p_password !~ '[0-9]' then
    raise exception 'contrasena_invalida' using errcode = '22023';
  end if;
  update auth.users
     set encrypted_password = extensions.crypt(p_password, extensions.gen_salt('bf', 10)),
         updated_at = now()
   where id = p_usuario;
  if not found then
    raise exception 'usuario_inexistente' using errcode = 'P0002';
  end if;
end;
$function$
"""

FUNCION_CERRAR = """
create or replace function public.cerrar_sesiones(p_usuario uuid, p_excepto uuid default null)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  delete from auth.sessions
   where user_id = p_usuario and (p_excepto is null or id <> p_excepto);
end;
$function$
"""


def upgrade() -> None:
    op.execute(FUNCION_FIJAR)
    op.execute(FUNCION_CERRAR)  # destructivo-aprobado: HU-B-403
    for funcion in FUNCIONES:
        op.execute(f"revoke execute on function {funcion} from public, anon, authenticated")


def downgrade() -> None:
    for funcion in FUNCIONES:
        op.execute(f"drop function {funcion}")
