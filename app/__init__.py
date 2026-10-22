from flask import Flask
from flask_cors import CORS

from app.api.v1 import register_blueprints
from app.container import rol_de_usuario
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.security import configurar_proveedor_rol


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    settings.url_base_de_datos()  # la app no arranca sin DATABASE_URL
    configure_logging(settings.log_level)

    app = Flask(__name__)
    CORS(app, origins=settings.cors_origins)
    register_error_handlers(app)
    register_blueprints(app)
    configurar_proveedor_rol(app, rol_de_usuario)

    return app
