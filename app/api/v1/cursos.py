from flask import Blueprint, request

from app.container import curso_service, solicitud_inscripcion_service
from app.core.constants import ROL_ESTUDIANTE
from app.core.limites import limiter, por_usuario
from app.core.responses import created, ok
from app.core.security import get_current_user, roles_required
from app.schemas.curso import MisCursosQuery, UnirseCursoIn

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
    """Cursos activos en los que esta inscrito el estudiante, con su avance y estado (HU-B-502).
    ?estado=sin_iniciar|en_curso|finalizado y ?orden=ultimo_avance|nombre|avance."""
    filtros = MisCursosQuery.model_validate(request.args.to_dict())
    return ok(curso_service().mis_cursos(get_current_user().id, **filtros.model_dump()))


@bp.get("/cursos/<int:curso_id>/retroalimentaciones")
@roles_required(ROL_ESTUDIANTE)
def mis_retroalimentaciones(curso_id: int):
    """Comentarios de mi docente en este curso (los marca como leidos)."""
    return ok(curso_service().mis_retroalimentaciones(get_current_user().id, curso_id))


@bp.get("/cursos/catalogo")
@roles_required(ROL_ESTUDIANTE)
def catalogo():
    """Todos los cursos activos para pedir inscripcion (HU-B-414). `mi_estado`: inscrito,
    pendiente (esperando respuesta), rechazada o null. Sin docente: `docente_nombre` es null."""
    return ok(solicitud_inscripcion_service().catalogo(get_current_user().id))


@bp.post("/cursos/<int:curso_id>/solicitudes")
@roles_required(ROL_ESTUDIANTE)
@limiter.limit(INTENTOS_UNIRSE, key_func=por_usuario)
def solicitar_inscripcion(curso_id: int):
    """Pide entrar a un curso: el docente del curso o un admin la acepta o la rechaza. 409 si ya
    estas inscrito o ya tienes una pendiente."""
    solicitud = solicitud_inscripcion_service().solicitar(get_current_user().id, curso_id)
    return created(solicitud, mensaje="Enviamos tu solicitud. Te avisaremos cuando la respondan.")


@bp.delete("/cursos/<int:curso_id>/solicitudes")
@roles_required(ROL_ESTUDIANTE)
def cancelar_solicitud(curso_id: int):
    """Retira tu solicitud pendiente a ese curso."""
    solicitud_inscripcion_service().cancelar(get_current_user().id, curso_id)
    return ok(None, mensaje="Cancelamos tu solicitud.")
