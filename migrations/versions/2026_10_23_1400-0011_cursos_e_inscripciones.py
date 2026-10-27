"""cursos, inscripciones, ruta del curso y retroalimentaciones

HU: HU-B-307
Revision ID: 0011
Revises: 0010
Create Date: 2026-10-23 14:00:00+00:00
Tipo: esquema
Destructiva: no

Politica de borrado (contrato de BD, seccion 4):
  profiles (docente) -> cursos.docente_id            RESTRICT (primero se reasigna el curso)
  cursos   -> inscripciones, curso_bloques, retroalimentaciones   CASCADE
  profiles -> inscripciones.estudiante_id, retroalimentaciones.estudiante_id   CASCADE
  profiles -> retroalimentaciones.docente_id          SET NULL (el comentario sigue siendo util)
  bloques  -> curso_bloques                           CASCADE
RLS activo y SIN politicas: solo el backend accede (con su propia conexion).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NIVELES = "nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])"
TABLAS = ("cursos", "inscripciones", "curso_bloques", "retroalimentaciones")


def _ahora(nombre: str) -> sa.Column:
    return sa.Column(
        nombre, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


def _fk(tabla: str, columna: str, destino: str, al_borrar: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [columna],
        [f"{destino}.id"],
        ondelete=al_borrar,
        name=op.f(f"fk_{tabla}_{columna}_{destino}"),
    )


def _indices(tabla: str, columnas: tuple[str, ...]) -> None:
    for columna in columnas:
        op.create_index(op.f(f"ix_{tabla}_{columna}"), tabla, [columna])


def upgrade() -> None:
    op.create_table(
        "cursos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text()),
        sa.Column("docente_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "nivel", sa.Text(), nullable=False, server_default=sa.text("'principiante'::text")
        ),
        sa.Column("codigo_invitacion", sa.Text(), nullable=False),
        sa.Column("archivado_en", sa.DateTime(timezone=True)),
        _ahora("creado_en"),
        _ahora("actualizado_en"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cursos")),
        _fk("cursos", "docente_id", "profiles", "RESTRICT"),
        sa.UniqueConstraint("codigo_invitacion", name=op.f("uq_cursos_codigo_invitacion")),
        sa.CheckConstraint(NIVELES, name=op.f("ck_cursos_nivel")),
        sa.CheckConstraint("char_length(nombre) BETWEEN 3 AND 120", name=op.f("ck_cursos_nombre")),
        sa.CheckConstraint(
            "codigo_invitacion ~ '^[A-HJKMNP-Z2-9]{8}$'", name=op.f("ck_cursos_codigo_invitacion")
        ),
    )
    _indices("cursos", ("docente_id",))

    op.create_table(
        "inscripciones",
        sa.Column(
            "id", postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("curso_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(), nullable=False),
        _ahora("inscrito_en"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inscripciones")),
        _fk("inscripciones", "curso_id", "cursos", "CASCADE"),
        _fk("inscripciones", "estudiante_id", "profiles", "CASCADE"),
        sa.UniqueConstraint(
            "curso_id", "estudiante_id", name=op.f("uq_inscripciones_curso_id_estudiante_id")
        ),
    )
    # La UNIQUE (curso_id, estudiante_id) cubre curso_id; estudiante_id necesita el suyo.
    _indices("inscripciones", ("estudiante_id",))

    op.create_table(
        "curso_bloques",
        sa.Column("curso_id", sa.Integer(), nullable=False),
        sa.Column("bloque_id", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("curso_id", "bloque_id", name=op.f("pk_curso_bloques")),
        _fk("curso_bloques", "curso_id", "cursos", "CASCADE"),
        _fk("curso_bloques", "bloque_id", "bloques", "CASCADE"),
        sa.UniqueConstraint("curso_id", "orden", name=op.f("uq_curso_bloques_curso_id_orden")),
        sa.CheckConstraint("orden > 0", name=op.f("ck_curso_bloques_orden")),
    )
    _indices("curso_bloques", ("bloque_id",))

    op.create_table(
        "retroalimentaciones",
        sa.Column(
            "id", postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("curso_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(), nullable=False),
        sa.Column("docente_id", postgresql.UUID()),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("leida_en", sa.DateTime(timezone=True)),
        _ahora("creado_en"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retroalimentaciones")),
        _fk("retroalimentaciones", "curso_id", "cursos", "CASCADE"),
        _fk("retroalimentaciones", "estudiante_id", "profiles", "CASCADE"),
        _fk("retroalimentaciones", "docente_id", "profiles", "SET NULL"),
        sa.CheckConstraint(
            "char_length(mensaje) BETWEEN 1 AND 1000", name=op.f("ck_retroalimentaciones_mensaje")
        ),
    )
    _indices("retroalimentaciones", ("curso_id", "estudiante_id", "docente_id"))

    op.execute(
        "create trigger cursos_tocar_actualizado_en before update on public.cursos "
        "for each row execute function public.tocar_actualizado_en()"
    )
    for tabla in TABLAS:
        op.execute(f"alter table public.{tabla} enable row level security")


def downgrade() -> None:
    for tabla in reversed(TABLAS):
        op.drop_table(tabla)
