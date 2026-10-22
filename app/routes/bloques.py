from flask import Blueprint, jsonify
from ..extensions import supabase

bp = Blueprint("bloques", __name__)


@bp.route("/api/bloques", methods=["GET"])
def get_bloques():
    response = supabase.table("bloques").select("*").order("orden_index").execute()
    return jsonify(response.data)
