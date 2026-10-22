from flask import Blueprint, jsonify

from app.container import bloque_service

bp = Blueprint("bloques", __name__)


@bp.get("/bloques")
def listar_bloques():
    return jsonify(bloque_service().listar())
