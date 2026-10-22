from flask import Flask
from flask_cors import CORS

from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()

    app = Flask(__name__)
    CORS(app, origins=settings.cors_origins)

    from .routes.acordes import bp as acordes_bp
    from .routes.bloques import bp as bloques_bp
    from .routes.ejercicios import bp as ejercicios_bp
    from .routes.health import bp as health_bp
    from .routes.lecciones import bp as lecciones_bp
    from .routes.progreso import bp as progreso_bp
    from .routes.quiz import bp as quiz_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(lecciones_bp)
    app.register_blueprint(acordes_bp)
    app.register_blueprint(ejercicios_bp)
    app.register_blueprint(progreso_bp)
    app.register_blueprint(bloques_bp)
    app.register_blueprint(quiz_bp)

    return app
