# =========================================================
# Errores de la aplicacion. Los servicios los lanzan y un unico
# conjunto de handlers los convierte en la respuesta del contrato:
#   error -> code, message, details  (ver contrato de API, seccion 3)
# En las rutas legadas /api/* se conserva {"error": "<mensaje>"}.
# =========================================================
import logging
from typing import Any

from flask import Flask, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.core.responses import es_ruta_legada

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
}

MENSAJES_HTTP = {
    404: "La ruta solicitada no existe.",
    405: "Este método no está permitido en la ruta solicitada.",
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


class ErrorProveedor(AppError):
    """El proveedor de datos (Supabase) fallo. El detalle se registra en el log, no se expone."""


def _respuesta(status: int, code: str, mensaje: str, details: list[dict] | None = None):
    if es_ruta_legada():
        return jsonify({"error": mensaje}), status
    cuerpo: dict[str, Any] = {"code": code, "message": mensaje, "details": details or []}
    return jsonify({"error": cuerpo}), status


def _detalles_validacion(error: ValidationError) -> list[dict]:
    return [
        {"campo": ".".join(str(parte) for parte in e["loc"]), "mensaje": e["msg"]}
        for e in error.errors()
    ]


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def manejar_app_error(error: AppError):
        return _respuesta(error.status, error.code, error.mensaje, error.details)

    @app.errorhandler(ValidationError)
    def manejar_validacion(error: ValidationError):
        detalles = _detalles_validacion(error)
        # En /api/* el frontend actual muestra un solo texto: el primer error.
        mensaje = (
            detalles[0]["mensaje"] if es_ruta_legada() else ValidacionError.mensaje_por_defecto
        )
        return _respuesta(ValidacionError.status, ValidacionError.code, mensaje, detalles)

    @app.errorhandler(HTTPException)
    def manejar_http(error: HTTPException):
        status = error.code or 500
        mensaje = MENSAJES_HTTP.get(status, MENSAJE_ERROR_INTERNO)
        return _respuesta(status, CODIGOS_HTTP.get(status, "ERROR_HTTP"), mensaje)

    @app.errorhandler(Exception)
    def manejar_inesperado(error: Exception):
        logger.exception("Error no controlado", exc_info=error)
        return _respuesta(500, AppError.code, MENSAJE_ERROR_INTERNO)
