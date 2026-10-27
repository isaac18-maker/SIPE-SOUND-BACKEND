from flask import Flask

from app.api.v1 import (
    acordes,
    admin,
    admin_cursos,
    auth,
    bloques,
    cursos,
    docente,
    docente_progreso,
    ejercicios,
    evaluaciones,
    health,
    lecciones,
    me,
    mensajes,
    progreso_contenido,
    terminos,
)
from app.core.limites import configurar_limites
from app.core.responses import PREFIJO_V1

# La API solo existe bajo /api/v1: el prefijo /api sin version se retiro en HU-B-319.
BLUEPRINTS = (
    health,
    auth,
    bloques,
    lecciones,
    ejercicios,
    acordes,
    me,
    mensajes,
    admin,
    admin_cursos,
    progreso_contenido,
    cursos,
    evaluaciones,
    docente,
    docente_progreso,
    terminos,
)


def register_blueprints(app: Flask) -> None:
    configurar_limites(app)
    for modulo in BLUEPRINTS:
        app.register_blueprint(modulo.bp, url_prefix=PREFIJO_V1)
