from flask import Blueprint, Response, request

from app.container import auth_service, recuperacion_service, verificacion_service
from app.core.config import get_settings
from app.core.errors import ValidacionError
from app.core.limites import limiter
from app.core.responses import PREFIJO_V1, created, ok
from app.schemas.auth import (
    InicioSesionIn,
    OlvidoContrasenaIn,
    ReenvioVerificacionIn,
    RegistroIn,
    RestablecerContrasenaIn,
    VerificacionIn,
)
from app.services.auth_service import SesionEmitida

bp = Blueprint("auth", __name__)

# Por IP: los estudiantes de un colegio comparten IP, por eso el margen es amplio.
REGISTROS_POR_IP = "20 per hour"
INICIOS_POR_IP = "30 per minute"
RENOVACIONES_POR_IP = "60 per minute"
VERIFICACIONES_POR_IP = "10 per minute"
REENVIOS_POR_IP = "5 per hour"
OLVIDOS_POR_IP = "5 per hour"
RESTABLECIMIENTOS_POR_IP = "10 per minute"

# El refresh token solo viaja en esta cookie: httpOnly (JavaScript no la lee) y limitada
# a las rutas de autenticacion (no acompana al resto de peticiones).
COOKIE_REFRESCO = "sipe_refresh"
RUTA_COOKIE = f"{PREFIJO_V1}/auth"
DURACION_COOKIE_SEGUNDOS = 30 * 24 * 60 * 60
MENSAJE_SOLO_JSON = "La petición debe enviarse como JSON (Content-Type: application/json)."
PREFIJO_BEARER = "Bearer "


@bp.post("/auth/registro")
@limiter.limit(REGISTROS_POR_IP)
def registrar():
    """Registro: crea la cuenta en Supabase Auth y envia un codigo de 6 digitos al correo.

    Publico. La respuesta no revela si el correo ya estaba registrado. El rol lo asigna
    la base (estudiante, o docente si un admin preautorizo el correo y la persona verifica).
    """
    datos = RegistroIn.model_validate(request.get_json(silent=True) or {})
    return created(
        auth_service().registrar(datos),
        mensaje="Te enviamos un código de 6 dígitos a tu correo. Vence en 15 minutos.",
    )


@bp.post("/auth/verificacion")
@limiter.limit(VERIFICACIONES_POR_IP)
def verificar_correo():
    """Confirma el correo con el codigo recibido (6 digitos, 15 minutos, un solo uso).

    Publico. Un codigo errado, vencido o usado y un correo sin cuenta responden lo mismo.
    """
    datos = VerificacionIn.model_validate(request.get_json(silent=True) or {})
    verificacion_service().verificar(datos.email, datos.codigo)
    return ok(
        {"email": datos.email, "verificado": True}, mensaje="Listo, tu correo quedó confirmado."
    )


@bp.post("/auth/verificacion/reenviar")
@limiter.limit(REENVIOS_POR_IP)
def reenviar_verificacion():
    """Envia un codigo nuevo (el anterior deja de servir). Siempre 200 con el mismo texto."""
    datos = ReenvioVerificacionIn.model_validate(request.get_json(silent=True) or {})
    verificacion_service().enviar_codigo(datos.email)
    return ok(None, mensaje="Si el correo tiene una cuenta pendiente, te enviamos un código nuevo.")


@bp.post("/auth/contrasena/olvido")
@limiter.limit(OLVIDOS_POR_IP)
def olvido_contrasena():
    """Envia un enlace (15 minutos, un solo uso) para crear una contrasena nueva.

    Publico. Siempre 200 con el mismo texto: no revela si el correo tiene cuenta. Solo se
    envia a cuentas con el correo verificado; 1 enlace cada 2 minutos por cuenta.
    """
    datos = OlvidoContrasenaIn.model_validate(request.get_json(silent=True) or {})
    recuperacion_service().pedir_enlace(datos.email)
    return ok(
        None,
        mensaje=(
            "Si el correo tiene una cuenta, te enviamos un enlace para crear una contraseña "
            "nueva. Vence en 15 minutos."
        ),
    )


@bp.post("/auth/contrasena/restablecer")
@limiter.limit(RESTABLECIMIENTOS_POR_IP)
def restablecer_contrasena():
    """Fija la contrasena nueva con el token del enlace y cierra todas las sesiones.

    Publico. Un token vencido, usado o inexistente responde 422 con el mismo texto.
    """
    datos = RestablecerContrasenaIn.model_validate(request.get_json(silent=True) or {})
    recuperacion_service().restablecer(datos.token, datos.password)
    return ok(None, mensaje="Listo. Ya puedes iniciar sesión con tu contraseña nueva.")


@bp.post("/auth/sesion")
@limiter.limit(INICIOS_POR_IP)
def iniciar_sesion():
    """Inicio de sesion con correo y contrasena.

    Devuelve el access token (el frontend lo guarda en memoria y lo envia como Bearer) y
    deja el refresh token en la cookie httpOnly `sipe_refresh`.
    """
    datos = InicioSesionIn.model_validate(request.get_json(silent=True) or {})
    return _con_cookie(auth_service().iniciar_sesion(datos), "Sesión iniciada.")


@bp.post("/auth/sesion/renovar")
@limiter.limit(RENOVACIONES_POR_IP)
def renovar_sesion():
    """Nuevo access token a partir de la cookie `sipe_refresh` (rota el refresh token).

    Se llama al cargar la app y cuando el access token vence. Sin cookie valida: 401.
    """
    _exigir_json()
    sesion = auth_service().refrescar(request.cookies.get(COOKIE_REFRESCO))
    return _con_cookie(sesion, "Sesión renovada.")


@bp.delete("/auth/sesion")
def cerrar_sesion():
    """Cierra la sesion: revoca el refresh token en Supabase y borra la cookie.

    Siempre responde 200, aunque la sesion ya hubiera vencido.
    """
    _exigir_json()
    cabecera = request.headers.get("Authorization", "")
    token = (
        cabecera.removeprefix(PREFIJO_BEARER).strip()
        if cabecera.startswith(PREFIJO_BEARER)
        else None
    )
    auth_service().cerrar_sesion(token)
    respuesta, estado = ok(None, mensaje="Cerraste sesión.")
    _borrar_cookie(respuesta)
    return respuesta, estado


def _exigir_json() -> None:
    # Defensa CSRF: un formulario de otro sitio no puede enviar application/json sin
    # una peticion previa (preflight) que CORS rechaza para origenes no autorizados.
    if not request.is_json:
        raise ValidacionError(MENSAJE_SOLO_JSON)


def _con_cookie(sesion: SesionEmitida, mensaje: str) -> tuple[Response, int]:
    respuesta, estado = ok(sesion.publica, mensaje=mensaje)
    settings = get_settings()
    respuesta.set_cookie(
        COOKIE_REFRESCO,
        sesion.refresh_token,
        max_age=DURACION_COOKIE_SEGUNDOS,
        path=RUTA_COOKIE,
        httponly=True,
        secure=settings.cookie_segura,
        samesite=settings.auth_cookie_samesite,
    )
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, estado


def _borrar_cookie(respuesta: Response) -> None:
    settings = get_settings()
    respuesta.delete_cookie(
        COOKIE_REFRESCO,
        path=RUTA_COOKIE,
        httponly=True,
        secure=settings.cookie_segura,
        samesite=settings.auth_cookie_samesite,
    )
