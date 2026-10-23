# =========================================================
# Cliente minimo de Supabase Auth (GoTrue) para crear cuentas (HU-B-318).
# Usa la clave service_role: SOLO en el servidor, nunca en el frontend.
# Libreria estandar (urllib): sin dependencias nuevas.
# Nunca se registran contrasenas, tokens ni la clave en los logs.
# =========================================================
import json
import logging
from typing import Any
from urllib import error, parse, request

from app.core.config import get_settings
from app.core.errors import (
    AppError,
    Conflicto,
    DemasiadasSolicitudes,
    ServicioNoDisponible,
    ValidacionError,
)

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 15
HTTP_DATOS_INVALIDOS = {400, 409, 422}
HTTP_LIMITE = 429
CODIGOS_YA_EXISTE = {"email_exists", "user_already_exists"}
MENSAJE_CONTRASENA_DEBIL = (
    "La contraseña es demasiado débil. Usa al menos 8 caracteres con letras y números."
)


class ClienteSupabaseAuth:
    def registrar(self, *, email: str, password: str, nombre: str) -> dict[str, Any]:
        """Registro publico: Supabase envia el correo de confirmacion. El trigger
        on_auth_user_created crea el perfil con rol 'estudiante'."""
        cuerpo = {"email": email, "password": password, "data": {"nombre": nombre}}
        return self._enviar("signup", cuerpo, redirigir_a="/login")

    def invitar(self, *, email: str, nombre: str) -> dict[str, Any]:
        """Invitacion de administrador: Supabase envia un correo para crear la contrasena."""
        cuerpo = {"email": email, "data": {"nombre": nombre}}
        return self._enviar("invite", cuerpo, redirigir_a="/activar-cuenta")

    def _enviar(self, ruta: str, cuerpo: dict, *, redirigir_a: str) -> dict[str, Any]:
        settings = get_settings()
        clave = (
            settings.supabase_service_role_key.get_secret_value().strip()
            if settings.supabase_service_role_key
            else ""
        )
        if not clave:  # ausente o vacia: no se llama a Supabase
            raise ServicioNoDisponible(
                "El registro no está disponible: falta configurar SUPABASE_SERVICE_ROLE_KEY."
            )
        url = f"{settings.emisor_jwt}/{ruta}"
        if not url.startswith("https://"):
            # S310: urlopen aceptaria file:// u otros esquemas; solo se permite HTTPS.
            raise ServicioNoDisponible("SUPABASE_URL debe usar https://.")
        if settings.frontend_url:
            destino = settings.frontend_url.rstrip("/") + redirigir_a
            url += "?" + parse.urlencode({"redirect_to": destino})
        peticion = request.Request(  # noqa: S310 - esquema validado arriba (solo https)
            url,
            data=json.dumps(cuerpo).encode("utf-8"),
            method="POST",
            headers={
                "apikey": clave,
                "Authorization": f"Bearer {clave}",
                "Content-Type": "application/json",
            },
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
    codigo = detalle.get("error_code") or detalle.get("code") or ""
    # Solo se registran el estado y el codigo de Supabase, nunca el cuerpo enviado.
    logger.warning("Supabase Auth %s respondio %s (%s)", ruta, fallo.code, codigo)
    if fallo.code == HTTP_LIMITE:
        return DemasiadasSolicitudes()
    if codigo in CODIGOS_YA_EXISTE:
        return Conflicto("Ese correo ya tiene una cuenta.")
    if codigo == "weak_password":
        return ValidacionError(MENSAJE_CONTRASENA_DEBIL)
    if fallo.code in HTTP_DATOS_INVALIDOS:
        return ValidacionError("Los datos de la cuenta no son válidos.")
    return ServicioNoDisponible("El servicio de cuentas falló. Inténtalo más tarde.")
