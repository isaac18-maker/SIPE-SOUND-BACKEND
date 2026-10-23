from flask import Blueprint, request

from app.container import curso_service
from app.core.constants import ROL_ESTUDIANTE
from app.core.limites import limiter, por_usuario
from app.core.responses import ok
from app.core.security import get_current_user, roles_required
from app.schemas.curso import UnirseCursoIn

bp = Blueprint("cursos", __name__)

INTENTOS_UNIRSE = "10 per minute"


@bp.post("/cursos/unirse")
@roles_required(ROL_ESTUDIANTE)
@limiter.limit(INTENTOS_UNIRSE, key_func=por_usuario)
def unirse():
    """Inscribirse en un curso con el codigo de invitacion del docente."""
    entrada = UnirseCursoIn.model_validate(request.get_json(silent=True) or {})
    return ok(curso_service().unirse(get_current_user().id, entrada.codigo))


@bp.get("/cursos")
@roles_required(ROL_ESTUDIANTE)
def mis_cursos():
    """Cursos activos en los que esta inscrito el estudiante."""
    return ok(curso_service().mis_cursos(get_current_user().id))


@bp.get("/cursos/<int:curso_id>/retroalimentaciones")
@roles_required(ROL_ESTUDIANTE)
def mis_retroalimentaciones(curso_id: int):
    """Comentarios de mi docente en este curso (los marca como leidos)."""
    return ok(curso_service().mis_retroalimentaciones(get_current_user().id, curso_id))
