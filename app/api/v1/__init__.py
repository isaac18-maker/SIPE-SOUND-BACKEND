from flask import Flask

from app.api.v1 import acordes, bloques, ejercicios, health, lecciones, progreso, quiz

PREFIJO_API = "/api"

BLUEPRINTS = (health, bloques, lecciones, ejercicios, acordes, progreso, quiz)


def register_blueprints(app: Flask) -> None:
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_API)
