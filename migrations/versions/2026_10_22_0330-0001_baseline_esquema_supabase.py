"""baseline esquema supabase

HU: HU-B-303
Revision ID: 0001
Revises:
Create Date: 2026-10-22 03:30:00+00:00
Tipo: esquema
Destructiva: no

Recrea el esquema public tal como existia en Supabase el 2026-10-21
(db/legacy/INVENTARIO.md). La base de Supabase existente NO se migra con
esta revision: se marca con `alembic stamp 0001`. Solo crea entornos nuevos.

No incluye objetos que administra Supabase: la funcion public.rls_auto_enable()
y los event triggers (ensure_rls, issue_*, pgrst_*).
Requiere el esquema auth de Supabase (auth.users y auth.uid()).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NIVELES = "nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])"
TEXTO = sa.Text()
CREADO_EN = ("creado_en", sa.DateTime(timezone=True), sa.text("now()"))

# Los nombres de restricciones van con op.f(): Alembic aplicaria si no la
# convencion de nombres del proyecto y crearia "ck_acordes_acordes_tipo_check".
# Nombres heredados tal cual (con y sin tilde) para coincidir con la base real.
POLITICAS_LECTURA_PUBLICA = {
    "acordes": "Lectura pública acordes",
    "bloques": "Lectura publica bloques",
    "ejercicios": "Lectura pública ejercicios",
    "lecciones": "Lectura pública lecciones",
    "partituras": "Lectura pública partituras",
    "quiz_preguntas": "Lectura publica quiz_preguntas",
}
POLITICAS_PROPIAS = (
    ("profiles", "Ver propio perfil", "select", "using (auth.uid() = id)"),
    ("profiles", "Editar propio perfil", "update", "using (auth.uid() = id)"),
    ("progreso", "Ver propio progreso", "select", "using (auth.uid() = usuario_id)"),
    ("progreso", "Insertar propio progreso", "insert", "with check (auth.uid() = usuario_id)"),
    ("progreso", "Actualizar propio progreso", "update", "using (auth.uid() = usuario_id)"),
)
TABLAS = (
    "acordes",
    "bloques",
    "lecciones",
    "ejercicios",
    "partituras",
    "profiles",
    "progreso",
    "quiz_preguntas",
)

FUNCION_HANDLE_NEW_USER = """
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $function$
begin
  insert into public.profiles (id, nombre, nivel)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', new.email), 'principiante');
  return new;
end;
$function$
"""


def _creado_en() -> sa.Column:
    nombre, tipo, defecto = CREADO_EN
    return sa.Column(nombre, tipo, server_default=defecto, nullable=True)


def _crear_catalogo() -> None:
    op.create_table(
        "acordes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", TEXTO, nullable=False),
        sa.Column("tipo", TEXTO),
        sa.Column("descripcion", TEXTO),
        sa.Column("dificultad", TEXTO, server_default=sa.text("'facil'::text")),
        _creado_en(),
        sa.Column("diagram", postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id", name=op.f("acordes_pkey")),
        sa.UniqueConstraint("nombre", name=op.f("acordes_nombre_key")),
        sa.CheckConstraint(
            "dificultad = ANY (ARRAY['facil'::text, 'medio'::text, 'dificil'::text])",
            name=op.f("acordes_dificultad_check"),
        ),
        sa.CheckConstraint(
            "tipo = ANY (ARRAY['mayor'::text, 'menor'::text, 'septima'::text, 'disminuido'::text])",
            name=op.f("acordes_tipo_check"),
        ),
    )
    op.create_table(
        "bloques",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("titulo", TEXTO, nullable=False),
        sa.Column("descripcion", TEXTO),
        sa.Column("nivel", TEXTO, nullable=False, server_default=sa.text("'principiante'::text")),
        sa.Column("orden_index", sa.Integer(), nullable=False),
        _creado_en(),
        sa.PrimaryKeyConstraint("id", name=op.f("bloques_pkey")),
        sa.CheckConstraint(NIVELES, name=op.f("bloques_nivel_check")),
    )
    op.create_table(
        "lecciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("titulo", TEXTO, nullable=False),
        sa.Column("descripcion", TEXTO),
        sa.Column("nivel", TEXTO, nullable=False, server_default=sa.text("'principiante'::text")),
        sa.Column("duracion", TEXTO),
        sa.Column("acordes", postgresql.ARRAY(TEXTO)),
        sa.Column("temas", postgresql.ARRAY(TEXTO)),
        _creado_en(),
        sa.Column("contenido", TEXTO),
        sa.Column("bloque_id", sa.Integer()),
        sa.PrimaryKeyConstraint("id", name=op.f("lecciones_pkey")),
        sa.ForeignKeyConstraint(
            ["bloque_id"],
            ["bloques.id"],
            ondelete="SET NULL",
            name=op.f("lecciones_bloque_id_fkey"),
        ),
        sa.CheckConstraint(NIVELES, name=op.f("lecciones_nivel_check")),
    )
    op.create_table(
        "ejercicios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("leccion_id", sa.Integer()),
        sa.Column("nombre", TEXTO, nullable=False),
        sa.Column("descripcion", TEXTO),
        sa.Column("nivel", TEXTO, nullable=False, server_default=sa.text("'principiante'::text")),
        sa.Column("bpm_recomendado", sa.Integer(), server_default=sa.text("60")),
        sa.Column("duracion", TEXTO),
        sa.Column("compas", TEXTO, server_default=sa.text("'4/4'::text")),
        sa.Column("acordes", postgresql.ARRAY(TEXTO)),
        sa.Column("pasos", postgresql.ARRAY(TEXTO)),
        _creado_en(),
        sa.PrimaryKeyConstraint("id", name=op.f("ejercicios_pkey")),
        sa.ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            ondelete="SET NULL",
            name=op.f("ejercicios_leccion_id_fkey"),
        ),
        sa.CheckConstraint(NIVELES, name=op.f("ejercicios_nivel_check")),
    )
    op.create_table(
        "partituras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", TEXTO, nullable=False),
        sa.Column("artista", TEXTO),
        sa.Column("nivel", TEXTO, server_default=sa.text("'principiante'::text")),
        sa.Column("tipo", TEXTO),
        sa.Column("acordes", postgresql.ARRAY(TEXTO)),
        sa.Column("imagen_url", TEXTO),
        _creado_en(),
        sa.PrimaryKeyConstraint("id", name=op.f("partituras_pkey")),
        sa.CheckConstraint(NIVELES, name=op.f("partituras_nivel_check")),
        sa.CheckConstraint(
            "tipo = ANY (ARRAY['partitura'::text, 'tablatura'::text, 'ambas'::text])",
            name=op.f("partituras_tipo_check"),
        ),
    )
    op.create_table(
        "quiz_preguntas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bloque_id", sa.Integer(), nullable=False),
        sa.Column("pregunta", TEXTO, nullable=False),
        sa.Column("opciones", postgresql.ARRAY(TEXTO), nullable=False),
        sa.Column("respuesta_correcta", sa.Integer(), nullable=False),
        sa.Column("orden_index", sa.Integer(), nullable=False),
        _creado_en(),
        sa.PrimaryKeyConstraint("id", name=op.f("quiz_preguntas_pkey")),
        sa.ForeignKeyConstraint(
            ["bloque_id"],
            ["bloques.id"],
            ondelete="CASCADE",
            name=op.f("quiz_preguntas_bloque_id_fkey"),
        ),
    )


def _crear_tablas_de_usuario() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("nombre", TEXTO, nullable=False),
        sa.Column("nivel", TEXTO, nullable=False, server_default=sa.text("'principiante'::text")),
        _creado_en(),
        sa.PrimaryKeyConstraint("id", name=op.f("profiles_pkey")),
        sa.ForeignKeyConstraint(
            ["id"], ["auth.users.id"], ondelete="CASCADE", name=op.f("profiles_id_fkey")
        ),
        sa.CheckConstraint(NIVELES, name=op.f("profiles_nivel_check")),
    )
    op.create_table(
        "progreso",
        sa.Column(
            "id",
            postgresql.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", postgresql.UUID(), nullable=False),
        sa.Column("tipo", TEXTO, nullable=False),
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


def _crear_seguridad() -> None:
    for tabla in TABLAS:
        op.execute(f"alter table public.{tabla} enable row level security")
    for tabla, politica in POLITICAS_LECTURA_PUBLICA.items():
        op.execute(f'create policy "{politica}" on public.{tabla} for select using (true)')
    for tabla, politica, comando, condicion in POLITICAS_PROPIAS:
        op.execute(f'create policy "{politica}" on public.{tabla} for {comando} {condicion}')


def _crear_alta_de_perfiles() -> None:
    op.execute(FUNCION_HANDLE_NEW_USER)
    op.execute(
        "create trigger on_auth_user_created after insert on auth.users "
        "for each row execute function public.handle_new_user()"
    )


def upgrade() -> None:
    _crear_catalogo()
    _crear_tablas_de_usuario()
    _crear_seguridad()
    _crear_alta_de_perfiles()


def downgrade() -> None:
    # Solo tiene sentido en entornos creados con upgrade(); jamas sobre la base heredada.
    op.execute("drop trigger if exists on_auth_user_created on auth.users")
    op.execute("drop function if exists public.handle_new_user()")
    for tabla in reversed(TABLAS):
        op.drop_table(tabla)
