from flask import Blueprint, request

from app.container import terminos_service
from app.core.constants import ROL_ADMIN
from app.core.limites import limiter, por_usuario
from app.core.responses import ok
from app.core.security import auth_required, get_current_user, roles_required
from app.schemas.terminos import AceptarTerminosIn, TerminosEditarIn

bp = Blueprint("terminos", __name__)

INTENTOS_POR_MINUTO = "10 per minute"


@bp.get("/terminos")
def terminos_vigentes():
    """Publico: el texto vigente en Markdown y su version (lo lee el visitante y quien debe
    aceptarlo). No expone quien lo modifico."""
    vigente = terminos_service().vigente()
    return ok(
        {
            "version": vigente["version"],
            "contenido": vigente["contenido"],
            "actualizado_en": vigente["actualizado_en"],
        }
    )


@bp.post("/me/terminos")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def aceptar_terminos():
    """Acepta la version vigente. Solo auth_required: es lo que una cuenta con terminos
    pendientes puede hacer. 409 si la version enviada ya no es la vigente."""
    datos = AceptarTerminosIn.model_validate(request.get_json(silent=True) or {})
    return ok(terminos_service().aceptar(get_current_user(), datos.version), mensaje="Gracias.")


@bp.get("/admin/terminos")
@roles_required(ROL_ADMIN)
def terminos_para_editar():
    """El texto vigente con quien lo modifico por ultima vez y cuando."""
    return ok(terminos_service().vigente())


@bp.put("/admin/terminos")
@roles_required(ROL_ADMIN)
def editar_terminos():
    """Guarda el texto. `nueva_version: true` sube el numero: todas las cuentas deben leerlo y
    aceptarlo de nuevo para seguir; `false` corrige sin pedir nada."""
    datos = TerminosEditarIn.model_validate(request.get_json(silent=True) or {})
    vigente = terminos_service().actualizar(
        get_current_user(), datos.contenido, nueva_version=datos.nueva_version
    )
    return ok(vigente, mensaje="Guardamos los términos.")
