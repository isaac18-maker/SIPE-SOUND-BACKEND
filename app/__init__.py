from flask import Flask
from flask_cors import CORS

from app.api.v1 import register_blueprints
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()

    app = Flask(__name__)
    CORS(app, origins=settings.cors_origins)
    register_error_handlers(app)
    register_blueprints(app)

    return app
