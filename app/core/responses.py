# =========================================================
# Estructura UNICA de respuesta de la API v1 (HU-B-317), igual para
# exito y error:
#   statusCode, status, data, success, message, errors, timestamp, meta
# Las rutas legadas /api/* (sin version) conservan su forma anterior
# para no romper el frontend actual.
# TODO(HU-B-312): retirar el modo legado.
# =========================================================
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from flask import Response, jsonify, request

PREFIJO_V1 = "/api/v1"
MENSAJE_EXITO = "Operación exitosa."
MENSAJE_CREADO = "Recurso creado."


def es_ruta_legada() -> bool:
    return not request.path.startswith(PREFIJO_V1)


def marca_de_tiempo() -> str:
    """ISO-8601 en UTC con milisegundos: 2026-10-22T06:00:13.562Z."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def respuesta(
    status_code: int,
    *,
    data: Any = None,
    message: str,
    status: str | None = None,
    errors: list[str] | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[Response, int]:
    cuerpo = {
        "statusCode": status_code,
        "status": status or HTTPStatus(status_code).name,
        "data": data,
        "success": status_code < HTTPStatus.BAD_REQUEST,
        "message": message,
        "errors": errors or [],
        "timestamp": marca_de_tiempo(),
        "meta": meta or {},
    }
    return jsonify(cuerpo), status_code


def ok(
    data: Any, status: int = 200, *, mensaje: str = MENSAJE_EXITO, meta: dict | None = None
) -> tuple[Response, int]:
    if es_ruta_legada():
        return jsonify(data), status
    return respuesta(status, data=data, message=mensaje, meta=meta)


def created(data: Any, *, mensaje: str = MENSAJE_CREADO) -> tuple[Response, int]:
    return ok(data, status=HTTPStatus.CREATED, mensaje=mensaje)


def paginated(data: list[Any], *, pagina: int, por_pagina: int, total: int) -> tuple[Response, int]:
    meta = {"pagina": pagina, "por_pagina": por_pagina, "total": total}
    return ok(data, meta=meta)
