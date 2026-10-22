# =========================================================
# Respuestas exitosas con la forma del contrato de API:
#   {"data": ...}  o  {"data": [...], "meta": {...}}
# Las rutas legadas /api/* (sin version) devuelven el payload sin
# envolver para no romper el frontend actual.
# TODO(HU-B-312): retirar el modo legado.
# =========================================================
from typing import Any

from flask import Response, jsonify, request

PREFIJO_V1 = "/api/v1"


def es_ruta_legada() -> bool:
    return not request.path.startswith(PREFIJO_V1)


def ok(data: Any, status: int = 200) -> tuple[Response, int]:
    if es_ruta_legada():
        return jsonify(data), status
    return jsonify({"data": data}), status


def created(data: Any) -> tuple[Response, int]:
    return ok(data, status=201)


def no_content() -> tuple[str, int]:
    return "", 204


def paginated(data: list[Any], *, pagina: int, por_pagina: int, total: int) -> tuple[Response, int]:
    meta = {"pagina": pagina, "por_pagina": por_pagina, "total": total}
    return jsonify({"data": data, "meta": meta}), 200
