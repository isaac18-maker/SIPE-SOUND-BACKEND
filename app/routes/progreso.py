from flask import Blueprint, jsonify, request, g
from ..extensions import supabase
from ..auth import auth_required, supabase_rest

bp = Blueprint("progreso", __name__)


@bp.route("/api/progreso", methods=["GET"])
@auth_required
def get_progreso():
    resp = supabase_rest(
        "GET", "progreso", g.token,
        params={"usuario_id": f"eq.{g.user_id}"}
    )
    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@bp.route("/api/progreso", methods=["POST"])
@auth_required
def guardar_progreso():
    datos = request.get_json(silent=True)

    if not datos:
        return jsonify({"error": "Cuerpo de la peticion vacio o invalido"}), 400

    tipo = datos.get("tipo")
    contenido_id = datos.get("contenido_id")
    porcentaje = datos.get("porcentaje", 0)
    completado = datos.get("completado", False)

    if tipo not in ("leccion", "ejercicio"):
        return jsonify({"error": "El campo 'tipo' debe ser 'leccion' o 'ejercicio'"}), 400

    if not isinstance(contenido_id, int):
        return jsonify({"error": "El campo 'contenido_id' es obligatorio y debe ser un numero"}), 400

    if not isinstance(porcentaje, int) or porcentaje < 0 or porcentaje > 100:
        return jsonify({"error": "El campo 'porcentaje' debe ser un numero entre 0 y 100"}), 400

    tabla = "lecciones" if tipo == "leccion" else "ejercicios"
    existe = supabase.table(tabla).select("id").eq("id", contenido_id).execute()
    if not existe.data:
        return jsonify({"error": f"No existe {tipo} con id {contenido_id}"}), 404

    registro = {
        "usuario_id": g.user_id,
        "tipo": tipo,
        "contenido_id": contenido_id,
        "porcentaje": porcentaje,
        "completado": completado,
    }

    resp = supabase_rest(
        "POST", "progreso", g.token,
        params={"on_conflict": "usuario_id,tipo,contenido_id"},
        json_body=registro
    )

    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), resp.status_code

    return jsonify(resp.json()), 200
