from flask import Blueprint

from app.container import bloque_service
from app.core.responses import ok

bp = Blueprint("bloques", __name__)


@bp.get("/bloques")
def listar_bloques():
    return ok(bloque_service().listar())
