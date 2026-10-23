from flask import Blueprint

from app.core.responses import ok

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return ok({"status": "ok", "mensaje": "Backend funcionando"})
