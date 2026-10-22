from flask import Blueprint

from app.container import perfil_service
from app.core.responses import ok
from app.core.security import auth_required, get_current_user

bp = Blueprint("me", __name__)


@bp.get("/me")
@auth_required
def mi_perfil():
    return ok(perfil_service().mi_perfil(get_current_user()))
