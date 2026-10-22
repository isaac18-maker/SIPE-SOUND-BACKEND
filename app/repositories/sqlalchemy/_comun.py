# =========================================================
# Conversion de modelos ORM a filas (dict) con el mismo formato
# que devuelve la API REST de Supabase, para que cambiar de
# implementacion no cambie las respuestas.
# =========================================================
from datetime import datetime
from typing import Any

from sqlalchemy import inspect

from app.models.base import Base
from app.repositories.base import AbrirSesion, Fila

__all__ = ["AbrirSesion", "a_fila", "formatear_fecha"]


def formatear_fecha(valor: datetime) -> str:
    """Como PostgreSQL al serializar timestamptz a JSON: sin ceros finales en la fraccion."""
    texto = valor.isoformat()
    if valor.microsecond == 0:
        return texto
    fecha, _, zona = texto.partition("+")
    entero, _, fraccion = fecha.partition(".")
    return f"{entero}.{fraccion.rstrip('0')}+{zona}"


def a_fila(modelo: Base) -> Fila:
    fila: dict[str, Any] = {}
    for atributo in inspect(modelo).mapper.column_attrs:
        valor = getattr(modelo, atributo.key)
        fila[atributo.key] = formatear_fecha(valor) if isinstance(valor, datetime) else valor
    return fila
