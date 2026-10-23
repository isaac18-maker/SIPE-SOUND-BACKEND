from flask import Flask

from app.api.v1 import (
    acordes,
    admin,
    bloques,
    cursos,
    ejercicios,
    evaluaciones,
    health,
    lecciones,
    me,
    progreso_contenido,
    quiz,
)
from app.core.limites import configurar_limites
from app.core.responses import PREFIJO_V1

# La API solo existe bajo /api/v1: el prefijo /api sin version se retiro en HU-B-319.
BLUEPRINTS = (
    health,
    bloques,
    lecciones,
    ejercicios,
    acordes,
    quiz,
    me,
    admin,
    progreso_contenido,
    cursos,
    evaluaciones,
)


def register_blueprints(app: Flask) -> None:
    configurar_limites(app)
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_V1)
