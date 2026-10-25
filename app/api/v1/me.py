from flask import Blueprint, request

from app.container import cuenta_service, perfil_service
from app.core.limites import limiter, por_usuario
from app.core.responses import ok
from app.core.security import auth_required, get_current_user
from app.schemas.cuenta import (
    CambiarContrasenaIn,
    CambiarCorreoIn,
    ConfirmarCorreoIn,
    ConfirmarReautenticacionIn,
    ReautenticacionIn,
)
from app.schemas.perfil import PerfilEditarIn

bp = Blueprint("me", __name__)

# Por persona (no por IP: los colegios comparten IP). Cada cambio exige confirmar la identidad.
CODIGOS_DE_IDENTIDAD_POR_HORA = "5 per hour"
INTENTOS_POR_MINUTO = "10 per minute"


@bp.get("/me")
@auth_required
def mi_perfil():
    return ok(perfil_service().mi_perfil(get_current_user()))


@bp.patch("/me")
@auth_required
@limiter.limit(INTENTOS_POR_MINUTO, key_func=por_usuario)
def editar_mi_nombre():
    """Cambia el nombre y/o el apellido. Solo si un administrador habilito el permiso en esta
    cuenta (los administradores siempre pueden); si no, 403. Cualquier otro campo es un 400."""
    datos = PerfilEditarIn.model_validate(request.get_json(silent=True) or {})
    perfil = perfil_service().editar_nombre(get_current_user(), datos.cambios())
    return ok(perfil, mensaje="Listo, actualizamos tu nombre.")


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
