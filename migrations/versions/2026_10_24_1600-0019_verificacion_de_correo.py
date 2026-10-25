"""verificacion de correo propia: correo_verificado_en y codigos_verificacion

HU: HU-B-402
Revision ID: 0019
Revises: 0018
Create Date: 2026-10-24 16:00:00+00:00
Tipo: esquema
Destructiva: si   # destructivo-aprobado: HU-B-402 (retira un trigger; no borra datos)

El backend pasa a ser dueño de la verificacion del correo (00-decisiones-fase-4, seccion 2):
- profiles.correo_verificado_en: nulo = la cuenta no puede iniciar sesion ni usar la API.
- codigos_verificacion: solo el HMAC de cada codigo, vigencia maxima de 15 minutos en un CHECK
  y un unico codigo abierto por persona y proposito. RLS activo y sin politicas.
- El rol docente preautorizado se aplica al llenar correo_verificado_en (trigger sobre
  profiles), ya NO al confirmar auth.users.email_confirmed_at. Es obligatorio hacerlo aqui:
  al desactivar "Confirm email" en Supabase, email_confirmed_at se llena al registrarse y el
  trigger viejo daria el rol docente a quien use un correo preautorizado ajeno.
- handle_new_user() vuelve al cuerpo de 0013 (sin la rama "si nace confirmada").
Seguridad: se revoca EXECUTE a public, anon y authenticated en la funcion nueva.
El downgrade() restaura el trigger y las funciones de 0014.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | Sequence[str] | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "codigos_verificacion"
PROPOSITOS = (
    "verificar_correo",
    "restablecer_contrasena",
    "reautenticar",
    "reautenticado",
    "cambiar_correo",
)

FUNCION_VERIFICADO = """
create or replace function public.handle_profile_verificado()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_email text;
begin
  select email into v_email from auth.users where id = new.id;
  if v_email is not null then
    perform public.aplicar_docente_preautorizado(new.id, v_email);
  end if;
  return new;
end;
$function$
"""

TRIGGER_VERIFICADO = """
create trigger on_profile_verificado
after update of correo_verificado_en on public.profiles
for each row
when (old.correo_verificado_en is null and new.correo_verificado_en is not null)
execute function public.handle_profile_verificado()
"""

# --- Funciones de 0014, para el downgrade ---
FUNCION_CONFIRMADO_0014 = """
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

TRIGGER_CONFIRMADO_0014 = """
create trigger on_auth_user_confirmed
after update of email_confirmed_at on auth.users
for each row
when (old.email_confirmed_at is null and new.email_confirmed_at is not null)
execute function public.handle_user_confirmed()
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
FUNCION_NUEVO_USUARIO_0013 = (
    ENCABEZADO_NUEVO_USUARIO
    + """
  return new;
end;
$function$
"""
)
FUNCION_NUEVO_USUARIO_0014 = (
    ENCABEZADO_NUEVO_USUARIO
    + """
  if new.email_confirmed_at is not null then
    perform public.aplicar_docente_preautorizado(new.id, new.email);
  end if;
  return new;
end;
$function$
"""
)


def _ck(nombre: str, expresion: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{TABLA}_{nombre}"))


def upgrade() -> None:
    op.add_column("profiles", sa.Column("correo_verificado_en", sa.DateTime(timezone=True)))

    lista = ", ".join(f"'{p}'" for p in PROPOSITOS)
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("proposito", sa.Text(), nullable=False),
        sa.Column("codigo_hash", sa.Text(), nullable=False),
        sa.Column("email_destino", sa.Text(), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["profiles.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{TABLA}_usuario_id_profiles"),
        ),
        _ck("proposito", f"proposito in ({lista})"),
        _ck("codigo_hash", "codigo_hash ~ '^[0-9a-f]{64}$'"),
        _ck("email_destino", "char_length(email_destino) <= 254"),
        _ck("intentos", "intentos BETWEEN 0 AND 5"),
        _ck(
            "vigencia",
            "expira_en > creado_en AND expira_en <= creado_en + interval '15 minutes'",
        ),
        _ck("cerrado_una_vez", "usado_en IS NULL OR invalidado_en IS NULL"),
    )
    op.create_index(op.f(f"ix_{TABLA}_usuario_id"), TABLA, ["usuario_id"])
    op.create_index(
        "uq_codigos_verificacion_abierto",
        TABLA,
        ["usuario_id", "proposito"],
        unique=True,
        postgresql_where=sa.text("usado_en IS NULL AND invalidado_en IS NULL"),
    )
    op.execute(f"alter table public.{TABLA} enable row level security")

    # El rol docente se aplica al verificar el correo con NUESTRO codigo.
    op.execute(FUNCION_VERIFICADO)
    op.execute(TRIGGER_VERIFICADO)
    op.execute(
        "revoke execute on function public.handle_profile_verificado() from public, anon, authenticated"
    )

    # Se retira la logica basada en auth.users.email_confirmed_at (ver docstring).
    op.execute(
        "drop trigger if exists on_auth_user_confirmed on auth.users"
    )  # destructivo-aprobado: HU-B-402
    op.execute("drop function public.handle_user_confirmed()")  # destructivo-aprobado: HU-B-402
    op.execute(FUNCION_NUEVO_USUARIO_0013)


def downgrade() -> None:
    op.execute(FUNCION_NUEVO_USUARIO_0014)
    op.execute(FUNCION_CONFIRMADO_0014)
    op.execute(TRIGGER_CONFIRMADO_0014)
    op.execute(
        "revoke execute on function public.handle_user_confirmed() from public, anon, authenticated"
    )

    op.execute("drop trigger if exists on_profile_verificado on public.profiles")
    op.execute("drop function public.handle_profile_verificado()")
    op.drop_table(TABLA)
    op.drop_column("profiles", "correo_verificado_en")
