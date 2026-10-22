from flask import Blueprint

from app.container import ejercicio_service
from app.core.responses import ok

bp = Blueprint("ejercicios", __name__)


@bp.get("/ejercicios")
def listar_ejercicios():
    return ok(ejercicio_service().listar())
