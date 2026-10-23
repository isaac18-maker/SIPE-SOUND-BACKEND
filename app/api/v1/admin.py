from flask import Blueprint, request

from app.container import admin_usuarios_service, registro_service
from app.core.constants import ROL_ADMIN
from app.core.responses import created, ok
from app.core.security import roles_required
from app.schemas.perfil import CambioRolIn
from app.schemas.registro import InvitacionDocenteIn

bp = Blueprint("admin", __name__)


@bp.patch("/admin/usuarios/<uuid:usuario_id>/rol")
@roles_required(ROL_ADMIN)
def cambiar_rol(usuario_id):
    entrada = CambioRolIn.model_validate(request.get_json(silent=True) or {})
    return ok(admin_usuarios_service().cambiar_rol(str(usuario_id), entrada.rol))


@bp.post("/admin/docentes/invitaciones")
@roles_required(ROL_ADMIN)
def invitar_docente():
    """Invitar a un docente: recibe un correo para crear su contrasena y entra como docente."""
    datos = InvitacionDocenteIn.model_validate(request.get_json(silent=True) or {})
    return created(
        registro_service().invitar_docente(datos),
        mensaje=f"Invitación enviada a {datos.email}.",
    )
