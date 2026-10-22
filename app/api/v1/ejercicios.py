from flask import Blueprint, jsonify

from app.container import ejercicio_service

bp = Blueprint("ejercicios", __name__)


@bp.get("/ejercicios")
def listar_ejercicios():
    return jsonify(ejercicio_service().listar())
