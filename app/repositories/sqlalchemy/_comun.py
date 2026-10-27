# =========================================================
# Conversion de modelos ORM a filas (dict) con el mismo formato
# que devuelve la API REST de Supabase, para que cambiar de
# implementacion no cambie las respuestas.
# =========================================================
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import TextClause, inspect, text
from sqlalchemy.orm import Session

from app.models.base import Base
from app.repositories.base import AbrirSesion, Fila

__all__ = [
    "AbrirSesion",
    "a_fila",
    "filas_sql",
    "formatear_fecha",
    "valor_de_fila",
    "video_de_fila",
]


def formatear_fecha(valor: datetime) -> str:
    """Como PostgreSQL al serializar timestamptz a JSON: sin ceros finales en la fraccion."""
    texto = valor.isoformat()
    if valor.microsecond == 0:
        return texto
    fecha, _, zona = texto.partition("+")
    entero, _, fraccion = fecha.partition(".")
    return f"{entero}.{fraccion.rstrip('0')}+{zona}"


def valor_de_fila(valor: Any) -> Any:
    """Fechas como las serializa PostgreSQL y UUID como texto: el ORM (UUID(as_uuid=False)) ya
    los entrega como texto, y el SQL crudo debe verse igual (si no, `fila["id"] == usuario_id`
    compara un UUID con un str y nunca coincide)."""
    if isinstance(valor, datetime):
        return formatear_fecha(valor)
    if isinstance(valor, UUID):
        return str(valor)
    return valor


def filas_sql(sesion: Session, sql: str | TextClause, parametros: dict[str, Any]) -> list[Fila]:
    """Ejecuta SQL y devuelve filas listas para la API."""
    consulta = text(sql) if isinstance(sql, str) else sql
    return [
        {k: valor_de_fila(v) for k, v in f._mapping.items()}
        for f in sesion.execute(consulta, parametros)
    ]


def video_de_fila(fila: Fila) -> Fila:
    """video_youtube_id + video_inicio_seg -> `video: {youtube_id, inicio_seg}` (o None). Solo
    se devuelve el id: la URL original no se guarda. No toca filas sin esas columnas."""
    if "video_youtube_id" not in fila:
        return fila
    video_id = fila.pop("video_youtube_id")
    inicio = fila.pop("video_inicio_seg", None)
    fila["video"] = {"youtube_id": video_id, "inicio_seg": inicio} if video_id else None
    return fila


def a_fila(modelo: Base) -> Fila:
    fila: dict[str, Any] = {}
    for atributo in inspect(modelo).mapper.column_attrs:
        valor = getattr(modelo, atributo.key)
        fila[atributo.key] = formatear_fecha(valor) if isinstance(valor, datetime) else valor
    return video_de_fila(fila)
