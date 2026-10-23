from flask import Blueprint, request

from app.container import registro_service
from app.core.limites import limiter
from app.core.responses import created
from app.schemas.registro import RegistroIn

bp = Blueprint("auth", __name__)

# Por IP: los estudiantes de un colegio comparten IP, por eso el margen es amplio.
REGISTROS_POR_IP = "20 per hour"


@bp.post("/auth/registro")
@limiter.limit(REGISTROS_POR_IP)
def registrar():
    """Registro de estudiante: crea la cuenta y envia el correo de confirmacion.

    Publico. La respuesta no revela si el correo ya estaba registrado.
    Docentes: invitacion de un administrador. Administradores: nunca por esta via.
    """
    datos = RegistroIn.model_validate(request.get_json(silent=True) or {})
    return created(
        registro_service().registrar_estudiante(datos),
        mensaje="Te enviamos un correo para confirmar tu cuenta.",
    )
