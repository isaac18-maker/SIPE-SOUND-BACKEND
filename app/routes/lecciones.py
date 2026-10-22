from flask import Blueprint, jsonify
from ..extensions import supabase

bp = Blueprint("lecciones", __name__)


@bp.route("/api/lecciones", methods=["GET"])
def get_lecciones():
    response = supabase.table("lecciones").select("*").order("numero").execute()
    return jsonify(response.data)


@bp.route("/api/lecciones/<int:leccion_id>", methods=["GET"])
def get_leccion(leccion_id):
    response = supabase.table("lecciones").select("*").eq("id", leccion_id).single().execute()
    return jsonify(response.data)
