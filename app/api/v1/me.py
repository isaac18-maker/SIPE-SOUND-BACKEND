from flask import Blueprint, request

from app.container import (
    cuenta_service,
    perfil_service,
    solicitud_nombre_service,
    terminos_pendientes_de,
    terminos_service,
)
from app.core.constants import ROL_ADMIN, ROL_DOCENTE, ROL_ESTUDIANTE
from app.core.limites import limiter, por_usuario
from app.core.responses import ok
from app.core.security import auth_required, get_current_user, roles_required
from app.schemas.cuenta import (
    CambiarContrasenaIn,
    CambiarCorreoIn,
    ConfirmarCorreoIn,
    ConfirmarReautenticacionIn,
    ReautenticacionIn,
)
from app.schemas.mensajes import SolicitudNombreIn
from app.schemas.perfil import PerfilEditarIn

bp = Blueprint("me", __name__)

# Por persona (no por IP: los colegios comparten IP). Cada cambio exige confirmar la identidad.
CODIGOS_DE_IDENTIDAD_POR_HORA = "5 per hour"
INTENTOS_POR_MINUTO = "10 per minute"
SOLICITUDES_DE_NOMBRE_POR_HORA = "5 per hour"


@bp.get("/me")
@auth_required
def mi_perfil():
    usuario = get_current_user()
    perfil = perfil_service().mi_perfil(usuario)
    # La interfaz decide con esto si manda a leer y aceptar los terminos (HU-B-411).
    perfil["terminos_version_vigente"] = terminos_service().version_vigente()
    perfil["terminos_pendientes"] = terminos_pendientes_de(usuario.id)
    return ok(perfil)


@bp.patch("/me")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def editar_mi_nombre():
    """Cambia el nombre y/o el apellido. Solo si un administrador habilito el permiso en esta
    cuenta (los administradores siempre pueden); si no, 403. Cualquier otro campo es un 400."""
    datos = PerfilEditarIn.model_validate(request.get_json(silent=True) or {})
    perfil = perfil_service().editar_nombre(get_current_user(), datos.cambios())
    return ok(perfil, mensaje="Listo, actualizamos tu nombre.")


@bp.post("/me/solicitud-nombre")
# roles_required carga el rol desde la base: con auth_required solo, el rol seria el del token y el
# limite por hora (que se busca por rol) valdria 0, es decir, siempre 429.
@roles_required(ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN)
@limiter.limit(SOLICITUDES_DE_NOMBRE_POR_HORA, key_func=por_usuario)
def solicitar_cambio_de_nombre():
    """Un aviso a los administradores pidiendo que habiliten el cambio de nombre. Los
    administradores no lo necesitan (siempre pueden): reciben 422."""
    datos = SolicitudNombreIn.model_validate(request.get_json(silent=True) or {})
    resultado = solicitud_nombre_service().solicitar(get_current_user(), datos.cuerpo)
    return ok(resultado, mensaje="Avisamos a los administradores.", status=201)


@bp.get("/me/solicitud-nombre")
@roles_required(ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN)
def mi_solicitud_de_nombre():
    """Tu ultima solicitud de cambio de nombre (pendiente, aceptada o rechazada) o null."""
    return ok(solicitud_nombre_service().la_mia(get_current_user()))


@bp.post("/me/reautenticacion")
@auth_required
@limiter.limit(CODIGOS_DE_IDENTIDAD_POR_HORA, key_func=por_usuario)
def pedir_codigo_de_identidad():
    """Paso 1 para cambiar correo o contrasena: la contrasena actual. Envia un codigo al
    correo actual (10 minutos, un solo uso)."""
    datos = ReautenticacionIn.model_validate(request.get_json(silent=True) or {})
    resultado = cuenta_service().pedir_codigo_de_identidad(
        get_current_user(), datos.password_actual
    )
    return ok(resultado, mensaje="Te enviamos un código a tu correo actual.")


@bp.post("/me/reautenticacion/confirmar")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def confirmar_identidad():
    """Paso 2: el codigo. Devuelve un token_reautenticacion (5 minutos, un solo uso, atado a
    esta sesion) que autoriza UN cambio."""
    datos = ConfirmarReautenticacionIn.model_validate(request.get_json(silent=True) or {})
    return ok(
        cuenta_service().confirmar_identidad(get_current_user(), datos.codigo),
        mensaje="Identidad confirmada.",
    )


@bp.patch("/me/contrasena")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def cambiar_contrasena():
    """Cambia la contrasena. Cierra las demas sesiones; esta sigue abierta."""
    datos = CambiarContrasenaIn.model_validate(request.get_json(silent=True) or {})
    cuenta_service().cambiar_contrasena(
        get_current_user(), datos.token_reautenticacion, datos.password_nueva
    )
    return ok(None, mensaje="Tu contraseña cambió. Cerramos tus otras sesiones.")


@bp.post("/me/correo")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def pedir_cambio_de_correo():
    """Envia un codigo al correo NUEVO. El correo no cambia hasta confirmarlo."""
    datos = CambiarCorreoIn.model_validate(request.get_json(silent=True) or {})
    cuenta_service().pedir_cambio_de_correo(
        get_current_user(), datos.token_reautenticacion, datos.email_nuevo
    )
    return ok(None, mensaje="Te enviamos un código a tu correo nuevo. Vence en 15 minutos.")


@bp.post("/me/correo/confirmar")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def confirmar_cambio_de_correo():
    """Confirma el codigo del correo nuevo: cambia el correo, avisa al anterior y cierra las
    demas sesiones."""
    datos = ConfirmarCorreoIn.model_validate(request.get_json(silent=True) or {})
    resultado = cuenta_service().confirmar_cambio_de_correo(get_current_user(), datos.codigo)
    return ok(resultado, mensaje="Tu correo cambió.")
