from flask import Flask
from flask_cors import CORS

from app.api.documentacion import registrar_documentacion
from app.api.v1 import register_blueprints
from app.container import rol_de_usuario
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.security import configurar_proveedor_rol


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = Flask(__name__)
    # Respetar el orden de la respuesta estandar (statusCode, status, data, ...).
    app.json.sort_keys = False
    # Credenciales: la cookie httpOnly del refresh token (HU-B-322). Seguro porque los
    # origenes son explicitos (nunca "*", ver config).
    CORS(app, origins=settings.cors_origins, supports_credentials=True)
    register_error_handlers(app)
    register_blueprints(app)
    registrar_documentacion(app)
    configurar_proveedor_rol(app, rol_de_usuario)

    return app
