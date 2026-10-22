from flask import Blueprint, jsonify
from ..extensions import supabase

bp = Blueprint("ejercicios", __name__)


@bp.route("/api/ejercicios", methods=["GET"])
def get_ejercicios():
    response = supabase.table("ejercicios").select("*").execute()
    return jsonify(response.data)
