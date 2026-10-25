"""terminos y condiciones editables y aceptacion por version

HU: HU-B-411
Revision ID: 0026
Revises: 0025
Create Date: 2026-10-25 21:00:00+00:00
Tipo: esquema
Destructiva: no

- documentos_legales: el texto vigente de los terminos en Markdown, con su `version` y quien lo
  modifico por ultima vez (SET NULL si su cuenta se elimina). Una sola fila por `tipo`.
  RLS activo y sin politicas: solo el backend lee y escribe. Se siembra con el texto que estaba
  fijo en el frontend (version 1).
- profiles.terminos_version y terminos_aceptados_en: lo que cada persona acepto. Las cuentas que
  ya existen aceptaron la version 1 al registrarse (casilla obligatoria, HU-B-323), asi que se
  marcan con esa version y su fecha de creacion.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | Sequence[str] | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "documentos_legales"
TEXTO_INICIAL = "# Términos y condiciones de SIPE SOUND\n\n## 1. Sobre SIPE SOUND\n\nSIPE SOUND es una plataforma educativa para aprender guitarra, desarrollada como proyecto de tesis en el marco del SENA. Actualmente se encuentra en fase de desarrollo académico (MVP) y aún no tiene registro mercantil. Sus funciones pueden cambiar o interrumpirse mientras se mejora.\n\n## 2. Uso de la plataforma\n\nTu cuenta es personal y eres responsable de mantener tu contraseña en secreto. Te comprometes a usar la plataforma solo con fines de aprendizaje, sin copiar, distribuir ni vender sus contenidos, y sin intentar acceder a cuentas o datos de otras personas.\n\n## 3. Tratamiento de datos personales\n\nConforme a la Ley 1581 de 2012, te informamos que guardamos tu nombre, tu correo electrónico y tu progreso (lecciones, ejercicios y quizzes). Usamos estos datos para crear tu cuenta, guardar tu avance y mejorar la plataforma. Se almacenan mediante el servicio Supabase y no se venden a terceros. Tienes derecho a conocer, actualizar, rectificar y solicitar la eliminación de tus datos, o a revocar tu autorización, escribiendo a [correo de contacto pendiente de publicar].\n\n## 4. Propiedad intelectual\n\nDe acuerdo con la Ley 23 de 1982 sobre derechos de autor, el diseño, el código, los textos, los ejercicios y la marca SIPE SOUND pertenecen a sus autores. Al registrarte no adquieres derechos sobre ellos, solo un permiso personal de uso.\n\n## 5. Aceptación electrónica\n\nAl marcar la casilla de aceptación y crear tu cuenta, manifiestas de forma electrónica que leíste y aceptas estos términos, lo cual tiene validez según la Ley 527 de 1999 sobre comercio electrónico y mensajes de datos.\n\n## 6. Alcance del servicio\n\nPor ser un proyecto académico, el servicio se ofrece tal como está, sin garantía de disponibilidad continua. El contenido es de apoyo para el aprendizaje y no reemplaza la enseñanza de un profesor presencial.\n\n## 7. Cambios\n\nPodemos actualizar estos términos cuando el proyecto evolucione. Si el cambio es importante, te lo avisaremos en la plataforma.\n"


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("tipo", sa.Text(), server_default="terminos", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("actualizado_por", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actualizado_por"],
            ["profiles.id"],
            name=op.f("fk_documentos_legales_actualizado_por_profiles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documentos_legales")),
        sa.UniqueConstraint("tipo", name=op.f("uq_documentos_legales_tipo")),
        sa.CheckConstraint("tipo = 'terminos'", name=op.f("ck_documentos_legales_tipo")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_documentos_legales_version")),
        sa.CheckConstraint(
            "char_length(btrim(contenido)) BETWEEN 1 AND 60000",
            name=op.f("ck_documentos_legales_contenido"),
        ),
    )
    op.create_index(
        op.f("ix_documentos_legales_actualizado_por"), TABLA, ["actualizado_por"], unique=False
    )
    op.execute(f"alter table public.{TABLA} enable row level security")
    op.execute(
        sa.text(
            "insert into public.documentos_legales (tipo, version, contenido) values ('terminos', 1, :t)"
        ).bindparams(t=TEXTO_INICIAL)
    )

    op.add_column("profiles", sa.Column("terminos_version", sa.Integer(), nullable=True))
    op.add_column(
        "profiles", sa.Column("terminos_aceptados_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        "update public.profiles set terminos_version = 1, terminos_aceptados_en = coalesce(creado_en, now())"
    )


def downgrade() -> None:
    op.drop_column("profiles", "terminos_aceptados_en")
    op.drop_column("profiles", "terminos_version")
    op.drop_index(op.f("ix_documentos_legales_actualizado_por"), table_name=TABLA)
    op.drop_table(TABLA)
