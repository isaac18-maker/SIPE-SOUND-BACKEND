"""acciones_admin y envios_correo admiten la asignacion de cursos por el administrador

HU: HU-B-417
Revision ID: 0033
Revises: 0032
Create Date: 2026-10-27 02:00:00+00:00
Tipo: esquema
Destructiva: no

El admin es el unico que asigna y quita docentes de los cursos (HU-B-417) y cada accion queda en
acciones_admin y el docente recibe el correo `curso_asignado` (envios_correo). Se amplian los
CHECK de `acciones_admin.accion` (asignar_curso, quitar_docente_curso) y de `envios_correo.tipo`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033"
down_revision: str | Sequence[str] | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCIONES = "acciones_admin"
ENVIOS = "envios_correo"
CHECK_ACCION = f"ck_{ACCIONES}_accion"
CHECK_TIPO = f"ck_{ENVIOS}_tipo"
ACCIONES_ANTERIORES = (
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
ACCIONES_NUEVAS = ("asignar_curso", "quitar_docente_curso")
TIPOS_ANTERIORES = (
    "verificar_correo",
    "reautenticacion",
    "restablecer_contrasena",
    "contrasena_cambiada",
    "cambiar_correo",
    "correo_cambiado",
)
TIPOS_NUEVOS = ("curso_asignado",)


def _lista(columna: str, valores: Sequence[str]) -> str:
    return f"{columna} in (" + ", ".join(f"'{v}'" for v in valores) + ")"


def _reemplazar(tabla: str, nombre: str, columna: str, valores: Sequence[str]) -> None:
    op.drop_constraint(op.f(nombre), tabla, type_="check")  # destructivo-aprobado: HU-B-417
    op.create_check_constraint(op.f(nombre), tabla, _lista(columna, valores))


def upgrade() -> None:
    _reemplazar(ACCIONES, CHECK_ACCION, "accion", (*ACCIONES_ANTERIORES, *ACCIONES_NUEVAS))
    _reemplazar(ENVIOS, CHECK_TIPO, "tipo", (*TIPOS_ANTERIORES, *TIPOS_NUEVOS))


def downgrade() -> None:
    # Las filas con los valores nuevos no caben en los CHECK anteriores: se retiran antes.
    op.execute(
        "delete from public.acciones_admin "  # destructivo-aprobado: HU-B-417
        "where accion in ('asignar_curso', 'quitar_docente_curso')"
    )
    op.execute(
        "delete from public.envios_correo "  # destructivo-aprobado: HU-B-417
        "where tipo = 'curso_asignado'"
    )
    _reemplazar(ACCIONES, CHECK_ACCION, "accion", ACCIONES_ANTERIORES)
    _reemplazar(ENVIOS, CHECK_TIPO, "tipo", TIPOS_ANTERIORES)
