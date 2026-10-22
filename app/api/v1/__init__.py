from flask import Flask

from app.api.v1 import (
    acordes,
    admin,
    bloques,
    ejercicios,
    health,
    lecciones,
    me,
    progreso,
    progreso_contenido,
    quiz,
)
from app.core.responses import PREFIJO_V1

# TODO(HU-B-312): retirar el prefijo legado cuando el frontend use solo /api/v1.
PREFIJO_LEGADO = "/api"

BLUEPRINTS = (health, bloques, lecciones, ejercicios, acordes, progreso, quiz)
# Endpoints nuevos: solo existen bajo /api/v1 (el prefijo legado no crece).
BLUEPRINTS_SOLO_V1 = (me, admin, progreso_contenido)


def register_blueprints(app: Flask) -> None:
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_V1)
        app.register_blueprint(
            modulo.bp, url_prefix=PREFIJO_LEGADO, name=f"{modulo.bp.name}_legado"
        )
    for modulo in BLUEPRINTS_SOLO_V1:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_V1)
