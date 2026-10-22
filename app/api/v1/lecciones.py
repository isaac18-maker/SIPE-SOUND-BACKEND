from flask import Blueprint

from app.container import leccion_service
from app.core.responses import ok

bp = Blueprint("lecciones", __name__)


@bp.get("/lecciones")
def listar_lecciones():
    return ok(leccion_service().listar())


@bp.get("/lecciones/<int:leccion_id>")
def obtener_leccion(leccion_id: int):
    return ok(leccion_service().obtener(leccion_id))
