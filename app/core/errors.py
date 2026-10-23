# =========================================================
# Errores de la aplicacion. Los servicios los lanzan y un unico
# conjunto de handlers los convierte en la respuesta estandar
# (ver contrato de API, seccion 3).
# =========================================================
import logging
from typing import Any

from flask import Flask
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.core.responses import respuesta

logger = logging.getLogger(__name__)

MENSAJE_ERROR_INTERNO = "Ocurrió un error inesperado. Inténtalo de nuevo en unos minutos."

CODIGOS_HTTP = {
    400: "VALIDACION",
    401: "NO_AUTENTICADO",
    403: "SIN_PERMISO",
    404: "NO_ENCONTRADO",
    405: "METODO_NO_PERMITIDO",
    409: "CONFLICTO",
    422: "REGLA_NEGOCIO",
    429: "DEMASIADAS_SOLICITUDES",
    503: "SERVICIO_NO_DISPONIBLE",
}

MENSAJES_HTTP = {
    404: "La ruta solicitada no existe.",
    405: "Este método no está permitido en la ruta solicitada.",
    429: "Demasiados intentos. Espera un minuto e inténtalo de nuevo.",
}


# Codigos SQLSTATE de PostgreSQL para las restricciones de integridad.
SQLSTATE_UNICO = "23505"
# Restricciones unicas con un mensaje que dice que hacer.
MENSAJES_UNICOS = {
    "uq_evaluaciones_bloque_global": "Ese bloque ya tiene una evaluación vigente: ciérrala primero.",
    "uq_bloques_orden_index": "Ya hay un bloque en esa posición (orden_index).",
    "uq_preguntas_evaluacion_evaluacion_id_orden": "Dos preguntas no pueden tener el mismo orden.",
    "acordes_nombre_key": "Ya existe un acorde con ese nombre.",
}
MENSAJES_INTEGRIDAD = {
    "23514": "Un valor está fuera de los límites permitidos.",
    "23503": "Una referencia no existe o todavía está en uso.",
    "23502": "Falta un campo obligatorio.",
}


class AppError(Exception):
    status = 500
    code = "ERROR_INTERNO"
    mensaje_por_defecto = MENSAJE_ERROR_INTERNO

    def __init__(self, mensaje: str | None = None, *, details: list[dict] | None = None) -> None:
        self.mensaje = mensaje or self.mensaje_por_defecto
        self.details = details or []
        super().__init__(self.mensaje)


class ValidacionError(AppError):
    status, code = 400, "VALIDACION"
    mensaje_por_defecto = "Hay campos con errores."


class NoAutenticado(AppError):
    status, code = 401, "NO_AUTENTICADO"
    mensaje_por_defecto = "Necesitas iniciar sesión."


class SinPermiso(AppError):
    status, code = 403, "SIN_PERMISO"
    mensaje_por_defecto = "No tienes permiso para esta acción."


class NoEncontrado(AppError):
    status, code = 404, "NO_ENCONTRADO"
    mensaje_por_defecto = "El recurso no existe."


class Conflicto(AppError):
    status, code = 409, "CONFLICTO"


class ReglaNegocio(AppError):
    status, code = 422, "REGLA_NEGOCIO"


def _respuesta(status: int, code: str, mensaje: str, details: list[dict] | None = None):
    # Estructura estandar (HU-B-317): el codigo de error va en "status".
    errores = [
        f"{d['campo']}: {d['mensaje']}" if d.get("campo") else d["mensaje"] for d in details or []
    ]
    return respuesta(status, status=code, message=mensaje, errors=errores)


# Pydantic redacta sus mensajes en ingles; el contrato exige espanol para el usuario.
# Los errores propios (PydanticCustomError) ya vienen en espanol y se respetan.
MENSAJES_VALIDACION = {
    "missing": "Este campo es obligatorio.",
    "extra_forbidden": "Este campo no está permitido.",
    "int_type": "Debe ser un número entero.",
    "int_parsing": "Debe ser un número entero.",
    "bool_type": "Debe ser verdadero o falso.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "string_type": "Debe ser un texto.",
    "dict_type": "Debe ser un objeto.",
    "model_type": "Debe ser un objeto.",
    "less_than_equal": "Debe ser menor o igual a {le}.",
    "greater_than_equal": "Debe ser mayor o igual a {ge}.",
    "literal_error": "Debe ser uno de: {expected}.",
    "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "Debe tener como máximo {max_length} caracteres.",
    "too_long": "Debe tener como máximo {max_length} elementos.",
    "too_short": "Debe tener al menos {min_length} elementos.",
    "greater_than": "Debe ser mayor que {gt}.",
    "less_than": "Debe ser menor que {lt}.",
    "list_type": "Debe ser una lista.",
    "datetime_parsing": "Debe ser una fecha y hora ISO-8601 (2026-11-30T23:59:00Z).",
    "datetime_type": "Debe ser una fecha y hora ISO-8601 (2026-11-30T23:59:00Z).",
    "timezone_aware": "La fecha debe incluir la zona horaria (p. ej. Z o -05:00).",
    "enum": "Debe ser uno de: {expected}.",
}


def _mensaje_validacion(error: dict[str, Any]) -> str:
    if (
        error["type"] in {"string_too_short", "too_short"}
        and error.get("ctx", {}).get("min_length") == 1
    ):
        return "No puede estar vacío."
    plantilla = MENSAJES_VALIDACION.get(error["type"])
    if plantilla is None:
        return error["msg"].removeprefix("Value error, ")
    contexto = {k: str(v).replace(" or ", " o ") for k, v in error.get("ctx", {}).items()}
    return plantilla.format(**contexto)


def _detalles_validacion(error: ValidationError) -> list[dict]:
    return [
        {"campo": ".".join(str(parte) for parte in e["loc"]), "mensaje": _mensaje_validacion(e)}
        for e in error.errors()
    ]


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def manejar_app_error(error: AppError):
        return _respuesta(error.status, error.code, error.mensaje, error.details)

    @app.errorhandler(ValidationError)
    def manejar_validacion(error: ValidationError):
        detalles = _detalles_validacion(error)
        return _respuesta(
            ValidacionError.status,
            ValidacionError.code,
            ValidacionError.mensaje_por_defecto,
            detalles,
        )

    @app.errorhandler(IntegrityError)
    def manejar_integridad(error: IntegrityError):
        """Red de seguridad: la base rechazo algo que la API no valido antes."""
        sqlstate = getattr(error.orig, "sqlstate", None)
        restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        logger.warning("Restriccion de la base: %s (%s)", restriccion, sqlstate)
        if sqlstate == SQLSTATE_UNICO:
            mensaje = MENSAJES_UNICOS.get(restriccion, "Ya existe un registro con ese valor.")
            return _respuesta(409, Conflicto.code, mensaje)
        mensaje = MENSAJES_INTEGRIDAD.get(sqlstate)
        if mensaje is None:
            logger.exception("Error de integridad no clasificado", exc_info=error)
            return _respuesta(500, AppError.code, MENSAJE_ERROR_INTERNO)
        return _respuesta(400, ValidacionError.code, mensaje)

    @app.errorhandler(HTTPException)
    def manejar_http(error: HTTPException):
        status = error.code or 500
        mensaje = MENSAJES_HTTP.get(status, MENSAJE_ERROR_INTERNO)
        return _respuesta(status, CODIGOS_HTTP.get(status, "ERROR_HTTP"), mensaje)

    @app.errorhandler(Exception)
    def manejar_inesperado(error: Exception):
        logger.exception("Error no controlado", exc_info=error)
        return _respuesta(500, AppError.code, MENSAJE_ERROR_INTERNO)
