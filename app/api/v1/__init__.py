from flask import Flask

from app.api.v1 import acordes, bloques, ejercicios, health, lecciones, progreso, quiz
from app.core.responses import PREFIJO_V1

# TODO(HU-B-312): retirar el prefijo legado cuando el frontend use solo /api/v1.
PREFIJO_LEGADO = "/api"

BLUEPRINTS = (health, bloques, lecciones, ejercicios, acordes, progreso, quiz)


def register_blueprints(app: Flask) -> None:
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_V1)
        app.register_blueprint(
            modulo.bp, url_prefix=PREFIJO_LEGADO, name=f"{modulo.bp.name}_legado"
        )
