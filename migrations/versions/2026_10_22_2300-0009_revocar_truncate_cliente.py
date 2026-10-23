"""revocar TRUNCATE, TRIGGER y REFERENCES a los roles del cliente

HU: HU-B-316
Revision ID: 0009
Revises: 0008
Create Date: 2026-10-22 23:00:00+00:00
Tipo: esquema
Destructiva: no

Supabase concede por defecto a anon y authenticated TODOS los privilegios de tabla.
RLS controla SELECT/INSERT/UPDATE/DELETE, pero NO controla TRUNCATE: con ese privilegio
un cliente podria vaciar una tabla completa si alguna via lo expusiera. TRIGGER y
REFERENCES tampoco los necesita nunca el cliente. Defensa en profundidad (R7).

Tambien se quitan de los privilegios por defecto del rol postgres (el que ejecuta
las migraciones), para que las tablas futuras nazcan sin ellos.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUITAR = (
    "revoke truncate, references, trigger on all tables in schema public from anon, authenticated",
    "alter default privileges for role postgres in schema public "
    "revoke truncate, references, trigger on tables from anon, authenticated",
)
RESTAURAR = (
    "grant truncate, references, trigger on all tables in schema public to anon, authenticated",
    "alter default privileges for role postgres in schema public "
    "grant truncate, references, trigger on tables to anon, authenticated",
)


def upgrade() -> None:
    for sentencia in QUITAR:
        op.execute(sentencia)


def downgrade() -> None:
    for sentencia in RESTAURAR:
        op.execute(sentencia)
