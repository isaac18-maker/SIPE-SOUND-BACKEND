from flask import Flask
from flask_cors import CORS

from app.api.documentacion import registrar_documentacion
from app.api.v1 import register_blueprints
from app.container import estado_de_usuario, rol_de_usuario, terminos_pendientes_de
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.security import (
    configurar_proveedor_estado,
    configurar_proveedor_rol,
    configurar_proveedor_terminos,
)


def opciones_cors(settings: Settings) -> dict:
    """Opciones de CORS explicitas, para que la peticion preflight (OPTIONS) sea respondida.

    El navegador envia OPTIONS antes de cualquier peticion con `Authorization` o
    `Content-Type: application/json`. Si la respuesta no declara metodos, cabeceras y
    credenciales, la peticion real nunca sale. Los origenes siguen siendo la lista exacta.
    """
    return {
        "origins": settings.cors_origins,
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "Accept"],
        "expose_headers": ["Content-Type"],
        # Cookie httpOnly del refresh token (HU-B-322): el frontend usa credentials "include"
        # en /auth/*. Es seguro porque los origenes son explicitos (nunca "*", ver config).
        "supports_credentials": True,
        "max_age": 86400,  # el navegador recuerda el preflight 24 h
        "send_wildcard": False,
        "vary_header": True,
        "automatic_options": True,
    }


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = Flask(__name__)
    # Respetar el orden de la respuesta estandar (statusCode, status, data, ...).
    app.json.sort_keys = False
    CORS(app, **opciones_cors(settings))
    register_error_handlers(app)
    register_blueprints(app)
    registrar_documentacion(app)
    configurar_proveedor_rol(app, rol_de_usuario)
    configurar_proveedor_estado(app, estado_de_usuario)
    configurar_proveedor_terminos(app, terminos_pendientes_de)

    return app
