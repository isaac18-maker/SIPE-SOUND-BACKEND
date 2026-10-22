from flask import Blueprint

from app.container import acorde_service
from app.core.responses import ok

bp = Blueprint("acordes", __name__)


@bp.get("/acordes")
def listar_acordes():
    return ok(acorde_service().listar())
