# =========================================================
# Cliente minimo de Supabase Auth (GoTrue) para que el backend sea el
# unico que habla con el proveedor de identidad (HU-B-322).
# Usa la clave PUBLICA (anon / publishable): no ignora RLS ni crea cuentas
# con privilegios. Nunca la service_role (retirada en HU-B-321).
# Libreria estandar (urllib): sin dependencias nuevas.
# Nunca se registran contrasenas, tokens ni la clave en los logs.
# =========================================================
import json
import logging
from collections.abc import Callable
from typing import Any
from urllib import error, parse, request

from app.core.config import get_settings
from app.core.constants import MENSAJE_SIN_CONFIRMAR
from app.core.errors import (
    AppError,
    CuentaExistente,
    DemasiadasSolicitudes,
    NoAutenticado,
    ReglaNegocio,
    ServicioNoDisponible,
    ValidacionError,
)

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 15
HTTP_LIMITE = 429
HTTP_DATOS_INVALIDOS = {400, 409, 422}
HTTP_TOKEN_RECHAZADO = {401, 403}
CODIGOS_CREDENCIALES = {"invalid_credentials", "invalid_grant"}
CODIGOS_REFRESCO_INVALIDO = {
    "refresh_token_not_found",
    "refresh_token_already_used",
    "session_not_found",
    "session_expired",
}
MENSAJE_CREDENCIALES = "El correo o la contraseña no coinciden. Revísalos e inténtalo de nuevo."
MENSAJE_SESION_VENCIDA = "Tu sesión terminó. Inicia sesión de nuevo."
MENSAJE_CONTRASENA_DEBIL = (
    "La contraseña es demasiado débil. Usa al menos 8 caracteres con letras y números."
)


class ClienteSupabaseAuth:
    def registrar(self, *, email: str, password: str, nombre: str) -> dict[str, Any]:
        """Supabase envia el correo de confirmacion. El trigger handle_new_user crea el
        perfil con rol 'estudiante' (o 'docente' si el correo esta preautorizado)."""
        cuerpo = {"email": email, "password": password, "data": {"nombre": nombre}}
        return self._enviar("signup", cuerpo)

    def iniciar_sesion(self, *, email: str, password: str) -> dict[str, Any]:
        return self._enviar("token", {"email": email, "password": password}, grant="password")

    def refrescar(self, refresh_token: str) -> dict[str, Any]:
        cuerpo = {"refresh_token": refresh_token}
        return self._enviar("token", cuerpo, grant="refresh_token")

    def cerrar_sesion(self, access_token: str) -> None:
        """Revoca los refresh tokens de esta sesion (scope=local) en Supabase."""
        self._enviar("logout", None, consulta={"scope": "local"}, token_usuario=access_token)

    def _enviar(
        self,
        ruta: str,
        cuerpo: dict | None,
        *,
        grant: str | None = None,
        consulta: dict[str, str] | None = None,
        token_usuario: str | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        clave = (
            settings.supabase_anon_key.get_secret_value().strip()
            if settings.supabase_anon_key
            else ""
        )
        if not clave:  # ausente o vacia: no se llama a Supabase
            raise ServicioNoDisponible(
                "El inicio de sesión no está disponible: falta configurar SUPABASE_ANON_KEY."
            )
        url = f"{settings.emisor_jwt}/{ruta}"
        if not url.startswith("https://"):
            # S310: urlopen aceptaria file:// u otros esquemas; solo se permite HTTPS.
            raise ServicioNoDisponible("SUPABASE_URL debe usar https://.")
        parametros = dict(consulta or {})
        if grant:
            parametros["grant_type"] = grant
        if parametros:
            url += "?" + parse.urlencode(parametros)
        cabeceras = {"apikey": clave, "Content-Type": "application/json"}
        if token_usuario:
            cabeceras["Authorization"] = f"Bearer {token_usuario}"
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        peticion = request.Request(  # noqa: S310 - esquema validado arriba (solo https)
            url, data=datos, method="POST", headers=cabeceras
        )
        try:
            with request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:  # noqa: S310
                return json.loads(respuesta.read() or b"{}")
        except error.HTTPError as fallo:
            raise _traducir(ruta, fallo) from None
        except (error.URLError, TimeoutError) as fallo:
            logger.error("Supabase Auth %s no respondio: %s", ruta, type(fallo).__name__)
            raise ServicioNoDisponible("No pudimos conectar con el servicio de cuentas.") from None


def _traducir(ruta: str, fallo: error.HTTPError) -> AppError:
    try:
        detalle = json.loads(fallo.read() or b"{}")
    except ValueError:
        detalle = {}
    codigo = detalle.get("error_code") or detalle.get("code") or detalle.get("error") or ""
    # Solo se registran el estado y el codigo de Supabase, nunca el cuerpo enviado.
    logger.warning("Supabase Auth %s respondio %s (%s)", ruta, fallo.code, codigo)
    if fallo.code == HTTP_LIMITE:
        return DemasiadasSolicitudes()
    if codigo in ERRORES_POR_CODIGO:
        return ERRORES_POR_CODIGO[codigo]()
    if fallo.code in HTTP_TOKEN_RECHAZADO:
        return NoAutenticado(MENSAJE_SESION_VENCIDA)
    if fallo.code in HTTP_DATOS_INVALIDOS:
        return ValidacionError("Los datos de la cuenta no son válidos.")
    return ServicioNoDisponible("El servicio de cuentas falló. Inténtalo más tarde.")


# Codigo de error de Supabase -> error de la API con mensaje para la persona.
ERRORES_POR_CODIGO: dict[str, Callable[[], AppError]] = {
    "email_not_confirmed": lambda: ReglaNegocio(
        MENSAJE_SIN_CONFIRMAR, meta={"requiere_verificacion": True}
    ),
    # Con "Confirm email" desactivado Supabase avisa que el correo ya existe; el registro lo
    # absorbe para no revelar que cuentas existen.
    "user_already_exists": CuentaExistente,
    "email_exists": CuentaExistente,
    "weak_password": lambda: ValidacionError(MENSAJE_CONTRASENA_DEBIL),
    **dict.fromkeys(CODIGOS_CREDENCIALES, lambda: NoAutenticado(MENSAJE_CREDENCIALES)),
    **dict.fromkeys(CODIGOS_REFRESCO_INVALIDO, lambda: NoAutenticado(MENSAJE_SESION_VENCIDA)),
}
