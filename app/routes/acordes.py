from flask import Blueprint, jsonify
from ..extensions import supabase

bp = Blueprint("acordes", __name__)


@bp.route("/api/acordes", methods=["GET"])
def get_acordes():
    response = supabase.table("acordes").select("*").execute()
    return jsonify(response.data)
