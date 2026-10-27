"""mensajeria interna: mensajes y destinatarios

HU: HU-B-409
Revision ID: 0025
Revises: 0024
Create Date: 2026-10-25 01:00:00+00:00
Tipo: esquema
Destructiva: no

- mensajes: un mensaje de una persona (o de nadie, si su cuenta se elimino: SET NULL) con su
  alcance. hilo_id agrupa un mensaje y sus respuestas; el primer mensaje de un hilo tiene
  hilo_id = id. curso_id solo se usa con alcance 'curso' y es SET NULL (un curso puede
  borrarse); por eso el CHECK solo exige "curso_id no nulo => alcance curso".
- mensaje_destinatarios: quien recibe cada mensaje. Al enviar a un grupo los destinatarios se
  copian EN ESE MOMENTO (quien entra despues al curso no ve avisos viejos). El remitente
  tambien tiene fila (leido) para que el hilo aparezca en su bandeja. CASCADE con la cuenta
  del destinatario (derecho de supresion).
- Indices: (hilo_id, creado_en), (remitente_id, creado_en) y, para el contador de no leidos,
  (destinatario_id, leido_en, mensaje_id). Cada FK queda cubierta por un indice.
- RLS activo y sin politicas: solo el backend (rol de servidor) lee y escribe.
Los correos no se mezclan con esto: la mensajeria es interna y no envia correos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | Sequence[str] | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MENSAJES = "mensajes"
DESTINATARIOS = "mensaje_destinatarios"
ALCANCES = (
    "usuario",
    "curso",
    "estudiantes_docente",
    "rol_estudiante",
    "rol_docente",
    "rol_admin",
    "todos",
)


def _ck(tabla: str, nombre: str, expresion: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expresion, name=op.f(f"ck_{tabla}_{nombre}"))


def upgrade() -> None:
    lista = ", ".join(f"'{a}'" for a in ALCANCES)
    op.create_table(
        MENSAJES,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("remitente_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("asunto", sa.Text(), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("alcance", sa.Text(), nullable=False),
        sa.Column("curso_id", sa.Integer(), nullable=True),
        sa.Column("respuesta_a_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("hilo_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{MENSAJES}")),
        sa.ForeignKeyConstraint(
            ["remitente_id"],
            ["profiles.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{MENSAJES}_remitente_id_profiles"),
        ),
        sa.ForeignKeyConstraint(
            ["curso_id"],
            ["cursos.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{MENSAJES}_curso_id_cursos"),
        ),
        sa.ForeignKeyConstraint(
            ["respuesta_a_id"],
            [f"{MENSAJES}.id"],
            ondelete="SET NULL",
            name=op.f(f"fk_{MENSAJES}_respuesta_a_id_{MENSAJES}"),
        ),
        _ck(MENSAJES, "asunto", "char_length(btrim(asunto)) BETWEEN 3 AND 120"),
        _ck(MENSAJES, "cuerpo", "char_length(btrim(cuerpo)) BETWEEN 1 AND 4000"),
        _ck(MENSAJES, "alcance", f"alcance in ({lista})"),
        _ck(MENSAJES, "curso_solo_con_alcance_curso", "curso_id IS NULL OR alcance = 'curso'"),
    )
    op.create_index(op.f(f"ix_{MENSAJES}_curso_id"), MENSAJES, ["curso_id"])
    op.create_index(op.f(f"ix_{MENSAJES}_respuesta_a_id"), MENSAJES, ["respuesta_a_id"])
    op.create_index("ix_mensajes_hilo_creado", MENSAJES, ["hilo_id", "creado_en"])
    op.create_index("ix_mensajes_remitente_creado", MENSAJES, ["remitente_id", "creado_en"])

    op.create_table(
        DESTINATARIOS,
        sa.Column("mensaje_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("destinatario_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("leido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("mensaje_id", "destinatario_id", name=op.f(f"pk_{DESTINATARIOS}")),
        sa.ForeignKeyConstraint(
            ["mensaje_id"],
            [f"{MENSAJES}.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{DESTINATARIOS}_mensaje_id_{MENSAJES}"),
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_id"],
            ["profiles.id"],
            ondelete="CASCADE",
            name=op.f(f"fk_{DESTINATARIOS}_destinatario_id_profiles"),
        ),
    )
    op.create_index(
        "ix_mensaje_destinatarios_bandeja",
        DESTINATARIOS,
        ["destinatario_id", "leido_en", "mensaje_id"],
    )
    for tabla in (MENSAJES, DESTINATARIOS):
        op.execute(f"alter table public.{tabla} enable row level security")


def downgrade() -> None:
    op.drop_table(DESTINATARIOS)
    op.drop_table(MENSAJES)
