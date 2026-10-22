# =========================================================
# Entorno de Alembic con el sistema de proteccion del contrato de BD
# (docs/fase-1-contrato/05-contrato-base-datos.md, seccion 5):
#   P1  solo el esquema public: nunca auth, storage, realtime...
#   P2  autogenerate aborta ante operaciones destructivas
#   P4  produccion exige -x confirmar=production
#   P5  lock_timeout y statement_timeout
#   P6  una transaccion por revision
#   P7  comparacion de tipos y defaults
#   P8  DATABASE_URL (Session pooler o directa), nunca alembic.ini ni el
#       transaction pooler (puerto 6543)
# P3 y P9 los valida scripts/check_migrations.py.
# =========================================================
import logging
from collections.abc import Iterator
from logging.config import fileConfig

from alembic import context
from alembic.operations import ops
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

import app.models  # noqa: F401 - registra todos los modelos en Base.metadata
from app.core.config import get_settings
from app.infrastructure.database import normalizar_url, opciones_conexion
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

ESQUEMAS_GESTIONADOS = {None, "public"}
SENTENCIAS_DE_SESION = ("set lock_timeout = '5s'", "set statement_timeout = '60s'")
OPERACIONES_DESTRUCTIVAS = (
    ops.DropTableOp,
    ops.DropColumnOp,
    ops.DropConstraintOp,
    ops.DropIndexOp,
)


class MigracionBloqueada(RuntimeError):
    """Una proteccion del contrato de BD impidio continuar."""


def _argumentos() -> dict[str, str]:
    return context.get_x_argument(as_dictionary=True)


# --- P1: nunca tocar los esquemas que administra Supabase -----------------
def incluir_nombre(nombre: str | None, tipo: str, padres: dict) -> bool:  # noqa: ARG001
    if tipo == "schema":
        return nombre in ESQUEMAS_GESTIONADOS
    return True


def incluir_objeto(objeto, nombre, tipo, reflejado, comparado_con) -> bool:  # noqa: ARG001
    # auth.users solo se declara en los modelos para poder referenciarla con FK.
    return not (tipo == "table" and objeto.schema not in ESQUEMAS_GESTIONADOS)


# --- P2: autogenerate no propone borrados sin permiso explicito ------------
def _recorrer(operaciones: ops.OpContainer) -> Iterator[ops.MigrateOperation]:
    for operacion in operaciones.ops:
        if isinstance(operacion, ops.OpContainer):
            yield from _recorrer(operacion)
        else:
            yield operacion


def _es_destructiva(operacion: ops.MigrateOperation) -> bool:
    if isinstance(operacion, OPERACIONES_DESTRUCTIVAS):
        return True
    return isinstance(operacion, ops.AlterColumnOp) and operacion.modify_type is not None


def bloquear_destructivas(contexto, revision, directivas) -> None:  # noqa: ARG001
    if _argumentos().get("allow_destructive") == "true":
        return
    destructivas = [
        f"  - {type(operacion).__name__}: {operacion.to_diff_tuple()[:3]}"
        for directiva in directivas
        for operacion in _recorrer(directiva.upgrade_ops)
        if _es_destructiva(operacion)
    ]
    if destructivas:
        raise MigracionBloqueada(
            "Autogenerate propuso operaciones destructivas y NO se creo el archivo:\n"
            + "\n".join(destructivas)
            + "\nSi son intencionales: revisalas, pasa -x allow_destructive=true y marca cada"
            " operacion con '# destructivo-aprobado: HU-B-XXX'."
        )


# --- P8: la URL sale del entorno, nunca de alembic.ini ---------------------
PUERTO_TRANSACTION_POOLER = 6543


def _url_migraciones() -> str:
    url = get_settings().url_base_de_datos()
    if make_url(url).port == PUERTO_TRANSACTION_POOLER:
        raise MigracionBloqueada(
            "DATABASE_URL apunta al Transaction pooler (6543), que rompe el DDL. "
            "Usa el Session pooler o la conexion directa (puerto 5432)."
        )
    return url


# --- P4: produccion exige confirmacion; una base remota exige APP_ENV coherente
def _verificar_entorno() -> None:
    confirmado = _argumentos().get("confirmar") == "production"
    motivo = get_settings().motivo_para_bloquear_operacion(confirmado=confirmado)
    if motivo:
        raise MigracionBloqueada(
            f"{motivo} En produccion: toma el respaldo (scripts/respaldar_datos.py), revisa "
            "el SQL con --sql y agrega -x confirmar=production. No se abrio ninguna conexion."
        )


OPCIONES_COMUNES = {
    "target_metadata": Base.metadata,
    "include_name": incluir_nombre,
    "include_object": incluir_objeto,
    "compare_type": True,  # P7
    "compare_server_default": True,  # P7
    "transaction_per_migration": True,  # P6
    "process_revision_directives": bloquear_destructivas,  # P2
}


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade head --sql) para revisarlo."""
    context.configure(
        url=normalizar_url(_url_migraciones()),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **OPCIONES_COMUNES,
    )
    with context.begin_transaction():
        for sentencia in SENTENCIAS_DE_SESION:  # P5
            context.execute(sentencia)
        context.run_migrations()


def run_migrations_online() -> None:
    _verificar_entorno()
    url = _url_migraciones()
    engine = create_engine(
        normalizar_url(url), poolclass=pool.NullPool, connect_args=opciones_conexion(url)
    )
    with engine.connect() as conexion:
        for sentencia in SENTENCIAS_DE_SESION:  # P5: aplican a toda la sesion
            conexion.exec_driver_sql(sentencia)
        conexion.commit()
        context.configure(connection=conexion, **OPCIONES_COMUNES)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
