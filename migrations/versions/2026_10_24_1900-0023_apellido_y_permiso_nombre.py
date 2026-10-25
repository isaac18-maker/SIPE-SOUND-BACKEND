"""profiles: apellido y permiso del administrador para editar el nombre

HU: HU-B-407
Revision ID: 0023
Revises: 0022
Create Date: 2026-10-24 19:00:00+00:00
Tipo: esquema
Destructiva: no

- profiles.apellido (nulo en las cuentas existentes): mismos limites que el nombre
  (2-80, sin caracteres de control), pero opcional en la base.
- profiles.puede_editar_nombre: false por defecto. Solo un administrador lo activa; se aplica
  por persona (no hay interruptor global).
- handle_new_user() copia y normaliza raw_user_meta_data->>'apellido' igual que el nombre;
  si no viene o no cumple, queda nulo. CREATE OR REPLACE conserva los permisos de 0014.
El downgrade() restaura la funcion de 0013 (la vigente tras 0019) y quita las columnas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENCABEZADO = """
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_nombre text;
"""

CUERPO_NOMBRE = """
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
"""

FUNCION_CON_APELLIDO = (
    ENCABEZADO  # noqa: S608 - SQL constante, sin datos de usuario
    + "  v_apellido text;"
    + CUERPO_NOMBRE
    + """  v_apellido := btrim(regexp_replace(
    coalesce(new.raw_user_meta_data->>'apellido', ''), '[[:space:][:cntrl:]]+', ' ', 'g'));
  v_apellido := btrim(left(v_apellido, 80));
  if char_length(v_apellido) < 2 then
    v_apellido := null;
  end if;
  insert into public.profiles (id, nombre, apellido, nivel)
  values (new.id, v_nombre, v_apellido, 'principiante');
  return new;
end;
$function$
"""
)

FUNCION_0013 = (
    ENCABEZADO  # noqa: S608 - SQL constante, sin datos de usuario
    + CUERPO_NOMBRE
    + """  insert into public.profiles (id, nombre, nivel) values (new.id, v_nombre, 'principiante');
  return new;
end;
$function$
"""
)


def upgrade() -> None:
    op.add_column("profiles", sa.Column("apellido", sa.Text(), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "puede_editar_nombre", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.create_check_constraint(
        op.f("ck_profiles_apellido"),
        "profiles",
        "apellido IS NULL OR char_length(btrim(apellido)) BETWEEN 2 AND 80",
    )
    op.create_check_constraint(
        op.f("ck_profiles_apellido_sin_control"),
        "profiles",
        "apellido IS NULL OR apellido !~ '[[:cntrl:]]'",
    )
    op.execute(FUNCION_CON_APELLIDO)


def downgrade() -> None:
    op.execute(FUNCION_0013)
    op.drop_constraint(op.f("ck_profiles_apellido_sin_control"), "profiles", type_="check")
    op.drop_constraint(op.f("ck_profiles_apellido"), "profiles", type_="check")
    op.drop_column("profiles", "puede_editar_nombre")
    op.drop_column("profiles", "apellido")
