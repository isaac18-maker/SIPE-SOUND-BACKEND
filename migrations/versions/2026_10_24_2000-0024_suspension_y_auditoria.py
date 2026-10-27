"""suspension de cuentas, auditoria del administrador y eliminacion de cuentas

HU: HU-B-405
Revision ID: 0024
Revises: 0023
Create Date: 2026-10-24 20:00:00+00:00
Tipo: esquema
Destructiva: si   # destructivo-aprobado: HU-B-405 (eliminar_cuenta borra una cuenta al
                  # ejecutarse; la migracion en si no borra datos)

- profiles.suspendido_en y profiles.motivo_suspension (10-300, coherentes entre si): una
  cuenta suspendida no inicia sesion ni usa la API.
- acciones_admin: auditoria de lo que hace un administrador sobre una cuenta. usuario_id NO
  tiene FK a proposito: la auditoria sobrevive a la cuenta eliminada (guarda el correo
  enmascarado, nunca el completo). admin_id: profiles SET NULL (contrato de BD, seccion 4).
  RLS activo y sin politicas: solo el backend.
- eliminar_cuenta(usuario): SECURITY DEFINER; se niega con un administrador y borra la fila de
  auth.users (profiles, progreso, intentos, inscripciones y codigos caen por cascada;
  cursos.docente_id es RESTRICT, asi que un docente con cursos no se puede eliminar).
Seguridad: EXECUTE revocado a public, anon y authenticated.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | Sequence[str] | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "acciones_admin"
ACCIONES = (
    "reenviar_verificacion",
    "verificar_manual",
    "suspender",
    "reactivar",
    "eliminar",
    "cambiar_rol",
    "revocar_curso",
    "reasignar_curso",
    "permiso_nombre",
)
FUNCION = "public.eliminar_cuenta(uuid)"

FUNCION_ELIMINAR = """
create or replace function public.eliminar_cuenta(p_usuario uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if exists (select 1 from public.profiles where id = p_usuario and rol = 'admin') then
    raise exception 'no_se_elimina_admin' using errcode = '42501';
  end if;
  delete from auth.users where id = p_usuario;
  if not found then
    raise exception 'usuario_inexistente' using errcode = 'P0002';
  end if;
end;
$function$
"""


def _ck(nombre: str, expresion: str, tabla: str = TABLA) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{tabla}_{nombre}"))


def upgrade() -> None:
    op.add_column("profiles", sa.Column("suspendido_en", sa.DateTime(timezone=True)))
    op.add_column("profiles", sa.Column("motivo_suspension", sa.Text()))
    op.create_check_constraint(
        op.f("ck_profiles_suspension_coherente"),
        "profiles",
        "(suspendido_en IS NULL) = (motivo_suspension IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_profiles_motivo_suspension"),
        "profiles",
        "motivo_suspension IS NULL OR char_length(btrim(motivo_suspension)) BETWEEN 10 AND 300",
    )

    lista = ", ".join(f"'{a}'" for a in ACCIONES)
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("admin_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column(
            "detalle",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLA}")),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["profiles.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{TABLA}_admin_id_profiles"),
        ),
        _ck("accion", f"accion in ({lista})"),
        _ck("detalle", "jsonb_typeof(detalle) = 'object'"),
    )
    op.create_index(op.f(f"ix_{TABLA}_admin_id"), TABLA, ["admin_id"])
    op.create_index("ix_acciones_admin_usuario_creado", TABLA, ["usuario_id", "creado_en"])
    op.execute(f"alter table public.{TABLA} enable row level security")

    op.execute(FUNCION_ELIMINAR)  # destructivo-aprobado: HU-B-405
    op.execute(f"revoke execute on function {FUNCION} from public, anon, authenticated")


def downgrade() -> None:
    op.execute(f"drop function {FUNCION}")
    op.drop_table(TABLA)
    op.drop_constraint(op.f("ck_profiles_motivo_suspension"), "profiles", type_="check")
    op.drop_constraint(op.f("ck_profiles_suspension_coherente"), "profiles", type_="check")
    op.drop_column("profiles", "motivo_suspension")
    op.drop_column("profiles", "suspendido_en")
