from flask import Blueprint, g, jsonify, request

from app.container import quiz_service
from app.core.security import auth_required
from app.schemas.quiz import VerificarQuizIn

bp = Blueprint("quiz", __name__)


@bp.get("/quiz/<int:bloque_id>")
def obtener_quiz(bloque_id: int):
    """Publica: las preguntas sin la respuesta correcta."""
    return jsonify(quiz_service().obtener_preguntas(bloque_id))


@bp.post("/quiz/<int:bloque_id>/verificar")
@auth_required
def verificar_quiz(bloque_id: int):
    entrada = VerificarQuizIn.model_validate(request.get_json(silent=True) or {})
    resultado = quiz_service().verificar(bloque_id, entrada.respuestas, g.user_id, g.token)
    return jsonify(resultado)
