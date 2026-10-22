from flask import Blueprint, g, request

from app.container import progreso_service
from app.core.errors import ValidacionError
from app.core.responses import ok
from app.core.security import auth_required
from app.schemas.progreso import ProgresoCreate

bp = Blueprint("progreso", __name__)


@bp.get("/progreso")
@auth_required
def listar_progreso():
    return ok(progreso_service().listar(g.user_id, g.token))


@bp.post("/progreso")
@auth_required
def guardar_progreso():
    datos = request.get_json(silent=True)
    if not datos:
        raise ValidacionError("Cuerpo de la peticion vacio o invalido")
    entrada = ProgresoCreate.model_validate(datos)
    return ok(progreso_service().guardar(g.user_id, g.token, entrada))
