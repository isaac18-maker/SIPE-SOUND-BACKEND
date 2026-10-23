"""docentes preautorizados: el rol docente se asigna al confirmar el correo

HU: HU-B-321
Revision ID: 0014
Revises: 0013
Create Date: 2026-10-24 12:00:00+00:00
Tipo: esquema
Destructiva: no

Reemplaza la invitacion por la API de Supabase (que exigia la clave service_role):
- docentes_preautorizados: correos que un admin autoriza (RLS sin politicas: solo backend).
- aplicar_docente_preautorizado(): marca la preautorizacion como usada y sube el perfil
  de 'estudiante' a 'docente'. Nunca toca a un admin (la preautorizacion queda pendiente).
- Se aplica cuando la cuenta CONFIRMA su correo (on_auth_user_confirmed) o al crearse
  ya confirmada (handle_new_user): registrarse con un correo ajeno no basta.
Seguridad: Supabase expone las funciones de public como RPC; se revoca EXECUTE a
public, anon y authenticated para que ningun cliente pueda llamarlas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "docentes_preautorizados"
FUNCIONES_PRIVADAS = (
    "public.aplicar_docente_preautorizado(uuid, text)",
    "public.handle_user_confirmed()",
    "public.handle_new_user()",
    "public.elementos_caben(text[], integer)",
)

FUNCION_APLICAR = """
create or replace function public.aplicar_docente_preautorizado(p_usuario uuid, p_email text)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  -- Un admin no se toca: la preautorizacion queda pendiente.
  if not exists (
    select 1 from public.profiles where id = p_usuario and rol in ('estudiante', 'docente')
  ) then
    return;
  end if;
  update public.docentes_preautorizados
     set usado_en = now(), usuario_id = p_usuario
   where email = lower(btrim(p_email)) and usado_en is null;
  if found then
    update public.profiles set rol = 'docente' where id = p_usuario and rol = 'estudiante';
  end if;
end;
$function$
"""

FUNCION_CONFIRMADO = """
create or replace function public.handle_user_confirmed()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
begin
  perform public.aplicar_docente_preautorizado(new.id, new.email);
  return new;
end;
$function$
"""

TRIGGER_CONFIRMADO = """
create trigger on_auth_user_confirmed
after update of email_confirmed_at on auth.users
for each row
when (old.email_confirmed_at is null and new.email_confirmed_at is not null)
execute function public.handle_user_confirmed()
"""

# Igual a la de 0013 + aplicar la preautorizacion si la cuenta nace confirmada.
CUERPO_NOMBRE = """
  v_nombre := regexp_replace(
    coalesce(new.raw_user_meta_data->>'nombre', ''), '[[:space:][:cntrl:]]+', ' ', 'g');
  v_nombre := btrim(v_nombre);
  if char_length(v_nombre) < 2 then
    v_nombre := btrim(split_part(coalesce(new.email, ''), '@', 1));
  end if;
  v_nombre := btrim(left(v_nombre, 80));
  if char_length(v_nombre) < 2 then
    v_nombre := 'Usuario';
  end if;
  insert into public.profiles (id, nombre, nivel) values (new.id, v_nombre, 'principiante');
"""
ENCABEZADO_NUEVO_USUARIO = """
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_nombre text;
begin
"""
FUNCION_NUEVO_USUARIO = (
    ENCABEZADO_NUEVO_USUARIO
    + CUERPO_NOMBRE
    + """
  if new.email_confirmed_at is not null then
    perform public.aplicar_docente_preautorizado(new.id, new.email);
  end if;
  return new;
end;
$function$
"""
)
FUNCION_NUEVO_USUARIO_0013 = (
    ENCABEZADO_NUEVO_USUARIO
    + CUERPO_NOMBRE
    + """
  return new;
end;
$function$
"""
)


def _fk(columna: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [columna],
        ["profiles.id"],
        ondelete="SET NULL",
        name=op.f(f"fk_{TABLA}_{columna}_profiles"),
    )


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("email", name=op.f(f"pk_{TABLA}")),
        _fk("creado_por"),
        _fk("usuario_id"),
        sa.CheckConstraint(
            "email = lower(btrim(email))", name=op.f(f"ck_{TABLA}_email_normalizado")
        ),
        sa.CheckConstraint("char_length(email) <= 254", name=op.f(f"ck_{TABLA}_email_largo")),
        sa.CheckConstraint(
            "email ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$'",
            name=op.f(f"ck_{TABLA}_email_formato"),
        ),
        sa.CheckConstraint(
            "(usado_en IS NULL) = (usuario_id IS NULL)", name=op.f(f"ck_{TABLA}_uso_coherente")
        ),
    )
    for columna in ("creado_por", "usuario_id"):
        op.create_index(op.f(f"ix_{TABLA}_{columna}"), TABLA, [columna])
    op.execute(f"alter table public.{TABLA} enable row level security")

    op.execute(FUNCION_APLICAR)
    op.execute(FUNCION_CONFIRMADO)
    op.execute(FUNCION_NUEVO_USUARIO)
    op.execute(TRIGGER_CONFIRMADO)
    for funcion in FUNCIONES_PRIVADAS:
        op.execute(f"revoke execute on function {funcion} from public, anon, authenticated")


def downgrade() -> None:
    op.execute("drop trigger if exists on_auth_user_confirmed on auth.users")
    op.execute(FUNCION_NUEVO_USUARIO_0013)
    op.execute("drop function public.handle_user_confirmed()")
    op.execute("drop function public.aplicar_docente_preautorizado(uuid, text)")
    for funcion in FUNCIONES_PRIVADAS[2:]:
        op.execute(f"grant execute on function {funcion} to public, anon, authenticated")
    op.drop_table(TABLA)
