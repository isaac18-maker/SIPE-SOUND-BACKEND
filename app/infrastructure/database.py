# =========================================================
# Conexion a PostgreSQL con SQLAlchemy. El engine se crea la primera
# vez que se pide. Los repositorios NO hacen commit: la unidad de
# trabajo es session_scope().
# =========================================================
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

PUERTO_POOLER_TRANSACCION = 6543


def normalizar_url(url: str) -> str:
    """Supabase entrega 'postgresql://'; SQLAlchemy necesita el driver psycopg 3 explicito."""
    return make_url(url).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def opciones_conexion(url: str) -> dict[str, Any]:
    # Fechas siempre en UTC, como las entrega la API de Supabase.
    opciones: dict[str, Any] = {"options": "-c timezone=UTC"}
    if make_url(url).port == PUERTO_POOLER_TRANSACCION:
        # El pooler en modo transaccion no soporta prepared statements.
        opciones["prepare_threshold"] = None
    return opciones


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.url_base_de_datos()
    return create_engine(
        normalizar_url(url),
        pool_pre_ping=True,
        connect_args=opciones_conexion(url),
        echo=settings.sqlalchemy_echo,
        # Los valores de las sentencias no salen en logs ni en errores: viajan contrasenas
        # (fijar_contrasena) y hashes de codigos. Con SQLALCHEMY_ECHO solo se ve el SQL.
        hide_parameters=True,
    )


@lru_cache
def _fabrica_sesiones() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Unidad de trabajo: commit si todo sale bien, rollback ante cualquier error."""
    sesion = _fabrica_sesiones()()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
