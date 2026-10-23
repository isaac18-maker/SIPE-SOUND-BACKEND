"""retirar quiz_preguntas y progreso (reemplazadas por evaluaciones y progreso_*)

HU: HU-B-312
Revision ID: 0017
Revises: 0016
Create Date: 2026-10-24 14:00:00+00:00
Tipo: esquema
Destructiva: si

Ningun endpoint las usa desde HU-B-308/HU-B-312. Guardia: aborta SIN borrar nada si
- algun bloque con preguntas en quiz_preguntas no tiene su evaluacion global con las
  mismas preguntas (0016), o
- alguna fila de progreso con contenido y perfil existentes no esta copiada
  (leccion -> progreso_lecciones, ejercicio -> progreso_ejercicios, bloque -> intento).
Las filas huerfanas (contenido o perfil borrados) no tienen destino y se descartan.
Antes de aplicar: uv run python -m scripts.respaldar_datos (P10).
downgrade() recrea ambas tablas VACIAS con su definicion, RLS, politicas y permisos;
los datos se restauran desde el respaldo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GUARDIA_TODO_COPIADO = """
do $$
declare
  sin_copiar integer;
begin
  select count(*) into sin_copiar
  from (select bloque_id, count(*) as n from public.quiz_preguntas group by bloque_id) q
  where not exists (
    select 1 from public.evaluaciones e
    where e.bloque_id = q.bloque_id and e.curso_id is null
      and (select count(*) from public.preguntas_evaluacion p where p.evaluacion_id = e.id)
          = q.n);
  if sin_copiar > 0 then
    raise exception '% bloque(s) con quiz sin evaluacion equivalente: aplica 0016', sin_copiar;
  end if;

  select count(*) into sin_copiar
  from public.progreso p
  where exists (select 1 from public.profiles f where f.id = p.usuario_id)
    and (
      (p.tipo = 'leccion'
        and exists (select 1 from public.lecciones l where l.id = p.contenido_id)
        and not exists (select 1 from public.progreso_lecciones x
                        where x.estudiante_id = p.usuario_id and x.leccion_id = p.contenido_id))
      or (p.tipo = 'ejercicio'
        and exists (select 1 from public.ejercicios j where j.id = p.contenido_id)
        and not exists (select 1 from public.progreso_ejercicios x
                        where x.estudiante_id = p.usuario_id and x.ejercicio_id = p.contenido_id))
      or (p.tipo = 'bloque'
        and exists (select 1 from public.quiz_preguntas q where q.bloque_id = p.contenido_id)
        and not exists (select 1 from public.intentos_evaluacion i
                        join public.evaluaciones e on e.id = i.evaluacion_id
                        where i.estudiante_id = p.usuario_id and e.bloque_id = p.contenido_id
                          and e.curso_id is null)));
  if sin_copiar > 0 then
    raise exception '% fila(s) de progreso sin copiar: aplica 0004 y 0016', sin_copiar;
  end if;
end $$
"""

POLITICAS_PROGRESO = (
    ("Ver propio progreso", "select", "using (auth.uid() = usuario_id)"),
    ("Insertar propio progreso", "insert", "with check (auth.uid() = usuario_id)"),
    ("Actualizar propio progreso", "update", "using (auth.uid() = usuario_id)"),
)


def upgrade() -> None:
    op.execute(GUARDIA_TODO_COPIADO)
    op.drop_table("quiz_preguntas")  # destructivo-aprobado: HU-B-312 (copiado en 0016)
    op.drop_table("progreso")  # destructivo-aprobado: HU-B-312 (copiado en 0004 y 0016)


def downgrade() -> None:
    op.create_table(
        "quiz_preguntas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bloque_id", sa.Integer(), nullable=False),
        sa.Column("pregunta", sa.Text(), nullable=False),
        sa.Column("opciones", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("respuesta_correcta", sa.Integer(), nullable=False),
        sa.Column("orden_index", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("quiz_preguntas_pkey")),
        sa.ForeignKeyConstraint(
            ["bloque_id"],
            ["bloques.id"],
            ondelete="CASCADE",
            name=op.f("quiz_preguntas_bloque_id_fkey"),
        ),
        sa.CheckConstraint(
            "respuesta_correcta >= 0 AND respuesta_correcta < cardinality(opciones)",
            name=op.f("ck_quiz_preguntas_respuesta_en_rango"),
        ),
    )
    op.create_table(
        "progreso",
        sa.Column(
            "id", postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("usuario_id", postgresql.UUID(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("contenido_id", sa.Integer(), nullable=False),
        sa.Column("porcentaje", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completado", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("progreso_pkey")),
        sa.UniqueConstraint(
            "usuario_id",
            "tipo",
            "contenido_id",
            name=op.f("progreso_usuario_id_tipo_contenido_id_key"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name=op.f("progreso_usuario_id_fkey"),
        ),
        sa.CheckConstraint(
            "porcentaje >= 0 AND porcentaje <= 100", name=op.f("progreso_porcentaje_check")
        ),
        sa.CheckConstraint(
            "tipo = ANY (ARRAY['leccion'::text, 'ejercicio'::text, 'bloque'::text])",
            name=op.f("progreso_tipo_check"),
        ),
    )
    for tabla in ("quiz_preguntas", "progreso"):
        op.execute(f"alter table public.{tabla} enable row level security")
    op.execute(
        'create policy "Lectura publica quiz_preguntas" on public.quiz_preguntas '
        "for select using (true)"
    )
    for politica, comando, condicion in POLITICAS_PROGRESO:
        op.execute(f'create policy "{politica}" on public.progreso for {comando} {condicion}')
    # 0005: la respuesta correcta no se expone a los clientes.
    op.execute("revoke select on public.quiz_preguntas from anon, authenticated")
    op.execute(
        "grant select (id, bloque_id, pregunta, opciones, orden_index, creado_en) "
        "on public.quiz_preguntas to anon, authenticated"
    )
