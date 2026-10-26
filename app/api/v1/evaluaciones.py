from flask import Blueprint, request

from app.container import evaluacion_service, rol_de_usuario, ruta_service
from app.core.constants import ROL_ESTUDIANTE
from app.core.responses import created, ok
from app.core.security import get_current_user, roles_required, usuario_opcional
from app.schemas.evaluacion import IntentoIn, RutaQuery

bp = Blueprint("evaluaciones", __name__)


@bp.get("/ruta")
def ruta():
    """Bloques de la ruta con estado (bloqueado, disponible, aprobado) y lecciones.

    Requiere sesion (HU-B-414). Un estudiante la ve solo si tiene una inscripcion aceptada (403
    si no); con ?curso_id= usa la ruta de ese curso (requiere estar inscrito o ser su docente).
    """
    filtros = RutaQuery.model_validate(request.args.to_dict())
    usuario = usuario_opcional()
    rol = rol_de_usuario(usuario.id) if usuario else None
    return ok(ruta_service().ruta(usuario.id if usuario else None, filtros.curso_id, rol))


@bp.get("/evaluaciones/<int:evaluacion_id>")
@roles_required(ROL_ESTUDIANTE)
def obtener(evaluacion_id: int):
    """Evaluacion con sus preguntas, sin respuestas correctas, y resumen de intentos."""
    return ok(evaluacion_service().obtener(evaluacion_id, get_current_user().id))


@bp.post("/evaluaciones/<int:evaluacion_id>/intentos")
@roles_required(ROL_ESTUDIANTE)
def presentar(evaluacion_id: int):
    """Presentar un intento: se califica, se guarda y se devuelve el detalle."""
    entrada = IntentoIn.model_validate(request.get_json(silent=True) or {})
    intento = evaluacion_service().presentar(
        evaluacion_id, get_current_user().id, entrada.respuestas
    )
    mensaje = "¡Aprobaste!" if intento["aprobado"] else "Intento registrado. ¡Sigue practicando!"
    return created(intento, mensaje=mensaje)


@bp.get("/evaluaciones/<int:evaluacion_id>/intentos")
@roles_required(ROL_ESTUDIANTE)
def historial(evaluacion_id: int):
    """Historial propio de intentos, del mas reciente al mas antiguo."""
    return ok(evaluacion_service().historial(evaluacion_id, get_current_user().id))
