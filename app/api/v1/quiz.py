from flask import Blueprint, request

from app.container import quiz_service
from app.core.responses import ok
from app.core.security import auth_required, get_current_user
from app.schemas.quiz import VerificarQuizIn

bp = Blueprint("quiz", __name__)


@bp.get("/quiz/<int:bloque_id>")
def obtener_quiz(bloque_id: int):
    """Publica: las preguntas sin la respuesta correcta."""
    return ok(quiz_service().obtener_preguntas(bloque_id))


@bp.post("/quiz/<int:bloque_id>/verificar")
@auth_required
def verificar_quiz(bloque_id: int):
    entrada = VerificarQuizIn.model_validate(request.get_json(silent=True) or {})
    usuario = get_current_user()
    resultado = quiz_service().verificar(bloque_id, entrada.respuestas, usuario.id)
    return ok(resultado)
