from flask import Blueprint, request

from app.container import progreso_service
from app.core.errors import ValidacionError
from app.core.responses import ok
from app.core.security import auth_required, get_current_user
from app.schemas.progreso import ProgresoCreate

bp = Blueprint("progreso", __name__)


@bp.get("/progreso")
@auth_required
def listar_progreso():
    usuario = get_current_user()
    return ok(progreso_service().listar(usuario.id, usuario.token))


@bp.post("/progreso")
@auth_required
def guardar_progreso():
    datos = request.get_json(silent=True)
    if not datos:
        raise ValidacionError("Cuerpo de la peticion vacio o invalido")
    entrada = ProgresoCreate.model_validate(datos)
    usuario = get_current_user()
    return ok(progreso_service().guardar(usuario.id, usuario.token, entrada))
