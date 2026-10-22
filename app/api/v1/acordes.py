from flask import Blueprint, jsonify

from app.container import acorde_service

bp = Blueprint("acordes", __name__)


@bp.get("/acordes")
def listar_acordes():
    return jsonify(acorde_service().listar())
