# =========================================================
# Errores de la aplicacion. Los servicios los lanzan y un unico
# handler los convierte en respuesta HTTP.
# TODO(HU-B-204): jerarquia completa y formato {"error": {code, message, details}}.
# Por ahora se conserva la forma actual {"error": "<mensaje>"}.
# =========================================================
from flask import Flask, jsonify
from pydantic import ValidationError


class AppError(Exception):
    status = 500

    def __init__(self, mensaje: str, status: int | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        if status is not None:
            self.status = status


class ValidacionError(AppError):
    status = 400


class NoEncontrado(AppError):
    status = 404


class ErrorProveedor(AppError):
    """El proveedor de datos (Supabase) respondio con error."""


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def manejar_app_error(error: AppError):
        return jsonify({"error": error.mensaje}), error.status

    @app.errorhandler(ValidationError)
    def manejar_validacion(error: ValidationError):
        # Forma actual: solo el primer error, en el orden de los campos del schema.
        return jsonify({"error": error.errors()[0]["msg"]}), ValidacionError.status
