"""evaluaciones, preguntas_evaluacion e intentos_evaluacion

HU: HU-B-308
Revision ID: 0015
Revises: 0014
Create Date: 2026-10-24 13:00:00+00:00
Tipo: esquema
Destructiva: no

Politica de borrado (contrato de BD, seccion 4):
  bloques  -> evaluaciones.bloque_id             CASCADE
  cursos   -> evaluaciones.curso_id              CASCADE
  profiles -> evaluaciones.autor_id              SET NULL
  evaluaciones -> preguntas, intentos            CASCADE
  profiles -> intentos_evaluacion.estudiante_id  CASCADE
Limites de 04-contrato-api seccion 7.2. opciones_validas() valida cada opcion del
arreglo JSON (un CHECK no admite subconsultas). RLS activo y sin politicas: solo backend.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("evaluaciones", "preguntas_evaluacion", "intentos_evaluacion")

# Arreglo de textos de min..max elementos, cada uno de 1..largo caracteres y sin repetidos
# (sin distinguir mayusculas).
FUNCION_OPCIONES = """
create or replace function public.opciones_validas(
  opciones jsonb, minimo integer, maximo integer, largo integer)
returns boolean
language sql
immutable
set search_path = ''
as $function$
  select jsonb_typeof(opciones) = 'array'
     and jsonb_array_length(opciones) between minimo and maximo
     and coalesce((
       select bool_and(jsonb_typeof(x) = 'string'
                       and char_length(btrim(x #>> '{}')) between 1 and largo)
          and count(distinct lower(btrim(x #>> '{}'))) = count(*)
       from jsonb_array_elements(opciones) as x), false)
$function$
"""


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


def _ck(tabla: str, nombre: str, expresion: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{tabla}_{nombre}"))


def _indices(tabla: str, columnas: tuple[str, ...]) -> None:
    for columna in columnas:
        op.create_index(op.f(f"ix_{tabla}_{columna}"), tabla, [columna])


def upgrade() -> None:
    op.execute(FUNCION_OPCIONES)
    op.execute(
        "revoke execute on function public.opciones_validas(jsonb, integer, integer, integer) "
        "from public, anon, authenticated"
    )

    t = "evaluaciones"
    op.create_table(
        t,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text()),
        sa.Column("bloque_id", sa.Integer()),
        sa.Column("curso_id", sa.Integer()),
        sa.Column("autor_id", postgresql.UUID()),
        sa.Column(
            "porcentaje_aprobacion", sa.Integer(), nullable=False, server_default=sa.text("80")
        ),
        sa.Column("intentos_max", sa.Integer()),
        sa.Column("fecha_limite", sa.DateTime(timezone=True)),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'borrador'::text")),
        _ahora("creado_en"),
        _ahora("actualizado_en"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _fk(t, "bloque_id", "bloques", "CASCADE"),
        _fk(t, "curso_id", "cursos", "CASCADE"),
        _fk(t, "autor_id", "profiles", "SET NULL"),
        _ck(t, "bloque_o_curso", "num_nonnulls(bloque_id, curso_id) >= 1"),
        _ck(t, "estado", "estado in ('borrador', 'publicada', 'cerrada')"),
        _ck(t, "titulo", "char_length(btrim(titulo)) BETWEEN 3 AND 120"),
        _ck(t, "descripcion", "char_length(descripcion) <= 2000"),
        _ck(
            t,
            "porcentaje_aprobacion",
            "porcentaje_aprobacion IS NULL OR "
            "(porcentaje_aprobacion >= 50 AND porcentaje_aprobacion <= 100)",
        ),
        _ck(
            t,
            "intentos_max",
            "intentos_max IS NULL OR (intentos_max >= 1 AND intentos_max <= 10)",
        ),
    )
    _indices(t, ("bloque_id", "curso_id", "autor_id"))
    op.create_index(
        "uq_evaluaciones_bloque_global",
        t,
        ["bloque_id"],
        unique=True,
        postgresql_where=sa.text("curso_id IS NULL AND estado <> 'cerrada'"),
    )
    op.execute(
        "create trigger evaluaciones_tocar_actualizado_en before update on public.evaluaciones "
        "for each row execute function public.tocar_actualizado_en()"
    )

    t = "preguntas_evaluacion"
    op.create_table(
        t,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluacion_id", sa.Integer(), nullable=False),
        sa.Column("enunciado", sa.Text(), nullable=False),
        sa.Column("opciones", postgresql.JSONB(), nullable=False),
        sa.Column("respuesta_correcta", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _fk(t, "evaluacion_id", "evaluaciones", "CASCADE"),
        sa.UniqueConstraint("evaluacion_id", "orden", name=op.f(f"uq_{t}_evaluacion_id_orden")),
        _ck(t, "orden", "orden > 0"),
        _ck(t, "enunciado", "char_length(btrim(enunciado)) BETWEEN 3 AND 300"),
        _ck(t, "opciones", "public.opciones_validas(opciones, 2, 6, 120)"),
        _ck(
            t,
            "respuesta_en_rango",
            "respuesta_correcta >= 0 AND respuesta_correcta < jsonb_array_length(opciones)",
        ),
    )
    _indices(t, ("evaluacion_id",))

    t = "intentos_evaluacion"
    op.create_table(
        t,
        sa.Column(
            "id", postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("evaluacion_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(), nullable=False),
        sa.Column("puntaje", sa.Integer(), nullable=False),
        sa.Column("correctas", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("aprobado", sa.Boolean(), nullable=False),
        sa.Column(
            "respuestas",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        _ahora("creado_en"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        _fk(t, "evaluacion_id", "evaluaciones", "CASCADE"),
        _fk(t, "estudiante_id", "profiles", "CASCADE"),
        _ck(t, "puntaje", "puntaje >= 0 AND puntaje <= 100"),
        _ck(t, "conteo", "total > 0 AND correctas >= 0 AND correctas <= total"),
        _ck(t, "respuestas", "jsonb_typeof(respuestas) = 'object'"),
    )
    _indices(t, ("estudiante_id",))
    op.create_index(
        op.f("ix_intentos_evaluacion_evaluacion_estudiante"),
        t,
        ["evaluacion_id", "estudiante_id"],
    )

    for tabla in TABLAS:
        op.execute(f"alter table public.{tabla} enable row level security")


def downgrade() -> None:
    for tabla in reversed(TABLAS):
        op.drop_table(tabla)
    op.execute("drop function public.opciones_validas(jsonb, integer, integer, integer)")
