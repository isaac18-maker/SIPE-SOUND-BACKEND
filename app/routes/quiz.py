from flask import Blueprint, jsonify, request, g
from ..extensions import supabase
from ..auth import auth_required, supabase_rest

bp = Blueprint("quiz", __name__)

PORCENTAJE_APROBACION = 80


# ---------------------------------------------------------
# Preguntas de un bloque, SIN la respuesta correcta.
# Publica: no requiere sesion.
# ---------------------------------------------------------
@bp.route("/api/quiz/<int:bloque_id>", methods=["GET"])
def get_quiz(bloque_id):
    response = (
        supabase.table("quiz_preguntas")
        .select("id, pregunta, opciones, orden_index")
        .eq("bloque_id", bloque_id)
        .order("orden_index")
        .execute()
    )
    return jsonify(response.data)


# ---------------------------------------------------------
# Califica el quiz y, si aprueba, guarda el progreso del bloque.
#
# Body esperado:
# {
#   "respuestas": { "3": 1, "4": 0, ... }   -- id_pregunta: indice elegido
# }
# ---------------------------------------------------------
@bp.route("/api/quiz/<int:bloque_id>/verificar", methods=["POST"])
@auth_required
def verificar_quiz(bloque_id):
    datos = request.get_json(silent=True)
    if not datos or "respuestas" not in datos:
        return jsonify({"error": "Falta el campo 'respuestas'"}), 400

    respuestas_usuario = datos["respuestas"]

    # Traemos las preguntas completas (con la respuesta correcta),
    # esto SOLO pasa en el backend, nunca se lo mandamos al frontend.
    preguntas = (
        supabase.table("quiz_preguntas")
        .select("id, respuesta_correcta")
        .eq("bloque_id", bloque_id)
        .execute()
    ).data

    if not preguntas:
        return jsonify({"error": "Este bloque no tiene preguntas"}), 404

    correctas = 0
    detalle = {}
    for pregunta in preguntas:
        pid = str(pregunta["id"])
        elegida = respuestas_usuario.get(pid)
        es_correcta = elegida == pregunta["respuesta_correcta"]
        detalle[pid] = {
            "correcta": es_correcta,
            "respuesta_correcta": pregunta["respuesta_correcta"],
        }
        if es_correcta:
            correctas += 1

    porcentaje = round((correctas / len(preguntas)) * 100)
    aprobado = porcentaje >= PORCENTAJE_APROBACION

    # Si el usuario ya habia aprobado este bloque antes, un intento
    # peor NO debe quitarle la aprobacion ni bajarle su mejor nota.
    previo = supabase_rest(
        "GET", "progreso", g.token,
        params={
            "usuario_id": f"eq.{g.user_id}",
            "tipo": "eq.bloque",
            "contenido_id": f"eq.{bloque_id}",
        },
    )
    ya_aprobado = False
    mejor_porcentaje = 0
    if previo.status_code < 400 and previo.json():
        fila = previo.json()[0]
        ya_aprobado = bool(fila.get("completado"))
        mejor_porcentaje = fila.get("porcentaje", 0)

    # Guardamos el mejor resultado y mantenemos "completado" si ya lo estaba
    registro = {
        "usuario_id": g.user_id,
        "tipo": "bloque",
        "contenido_id": bloque_id,
        "porcentaje": max(porcentaje, mejor_porcentaje),
        "completado": aprobado or ya_aprobado,
    }
    resp = supabase_rest(
        "POST", "progreso", g.token,
        params={"on_conflict": "usuario_id,tipo,contenido_id"},
        json_body=registro
    )
    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), resp.status_code

    return jsonify({
        "porcentaje": porcentaje,
        "correctas": correctas,
        "total": len(preguntas),
        "aprobado": aprobado,
        "minimo_requerido": PORCENTAJE_APROBACION,
        "detalle": detalle,
    })
