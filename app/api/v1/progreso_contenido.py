from flask import Blueprint, request

from app.container import progreso_service
from app.core.responses import ok
from app.core.security import auth_required, get_current_user
from app.schemas.progreso import ActividadQuery, AvanceEjercicioIn, AvanceIn

bp = Blueprint("progreso_contenido", __name__)


@bp.put("/progreso/lecciones/<int:leccion_id>")
@auth_required
def registrar_leccion(leccion_id: int):
    avance = AvanceIn.model_validate(request.get_json(silent=True) or {})
    return ok(progreso_service().registrar_leccion(get_current_user().id, leccion_id, avance))


@bp.put("/progreso/ejercicios/<int:ejercicio_id>")
@auth_required
def registrar_ejercicio(ejercicio_id: int):
    avance = AvanceEjercicioIn.model_validate(request.get_json(silent=True) or {})
    return ok(progreso_service().registrar_ejercicio(get_current_user().id, ejercicio_id, avance))


@bp.get("/progreso/resumen")
@auth_required
def resumen():
    return ok(progreso_service().resumen(get_current_user()))


@bp.get("/progreso/actividad")
@auth_required
def actividad():
    filtros = ActividadQuery.model_validate(request.args.to_dict())
    return ok(progreso_service().actividad(get_current_user(), filtros.dias))
