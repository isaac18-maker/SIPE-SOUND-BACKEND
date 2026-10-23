"""ocultar quiz_preguntas.respuesta_correcta a la anon key

HU: HU-B-313
Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22 18:00:00+00:00
Tipo: esquema
Destructiva: no

La politica RLS "Lectura publica quiz_preguntas" (select using true) sigue igual:
lo que cambia es QUE columnas puede leer el cliente. anon y authenticated pierden
respuesta_correcta; el backend la lee con su propia conexion (SqlQuizRepository).

Desplegar el codigo de HU-B-313 ANTES de aplicar esta revision: el backend anterior
leia respuesta_correcta con la anon key y dejaria de poder calificar.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sentencias literales (sin f-strings): faciles de auditar en una migracion de seguridad.
OCULTAR = (
    "revoke select on public.quiz_preguntas from anon, authenticated",
    "grant select (id, bloque_id, pregunta, opciones, orden_index, creado_en) "
    "on public.quiz_preguntas to anon, authenticated",
)
RESTAURAR = (
    "revoke select (id, bloque_id, pregunta, opciones, orden_index, creado_en) "
    "on public.quiz_preguntas from anon, authenticated",
    "grant select on public.quiz_preguntas to anon, authenticated",
)


def upgrade() -> None:
    for sentencia in OCULTAR:
        op.execute(sentencia)


def downgrade() -> None:
    for sentencia in RESTAURAR:
        op.execute(sentencia)
