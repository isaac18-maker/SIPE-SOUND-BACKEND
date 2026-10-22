from flask import Blueprint, jsonify

from app.container import leccion_service

bp = Blueprint("lecciones", __name__)


@bp.get("/lecciones")
def listar_lecciones():
    return jsonify(leccion_service().listar())


@bp.get("/lecciones/<int:leccion_id>")
def obtener_leccion(leccion_id: int):
    return jsonify(leccion_service().obtener(leccion_id))
