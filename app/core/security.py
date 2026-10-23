# =========================================================
# Autenticacion: valida localmente el JWT emitido por Supabase Auth
# (firma, exp, aud e iss) sin llamar a la red en cada peticion.
# Solo se descarga el JWKS publico del proyecto (cacheado); no hay secretos.
# =========================================================
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import lru_cache, wraps
from typing import Any

import jwt
from flask import Flask, current_app, g, request

from app.core.config import get_settings
from app.core.errors import NoAutenticado, SinPermiso

logger = logging.getLogger(__name__)

PREFIJO_BEARER = "Bearer "
AUDIENCIA = "authenticated"
ALGORITMOS_ASIMETRICOS = ["ES256", "RS256"]
TOLERANCIA_RELOJ_SEGUNDOS = 10
MENSAJE_FALTA_AUTENTICACION = "Falta el token de autenticacion"
MENSAJE_SESION_INVALIDA = "Token invalido o expirado"
MENSAJE_SIN_PERMISO = "No tienes permiso para esta sección."
CLAVE_PROVEEDOR_ROL = "sipe.proveedor_rol"

# Dado un id de usuario, devuelve su rol (o None si no tiene perfil).
ProveedorRol = Callable[[str], str | None]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    token: str
    rol: str | None = None  # se carga desde profiles solo cuando la ruta exige roles


def auth_required(f: Callable) -> Callable:
    """Exige un JWT valido de Supabase y deja el usuario en get_current_user()."""

    @wraps(f)
    def decorador(*args, **kwargs):
        token = _extraer_token(request.headers.get("Authorization", ""))
        reclamos = _decodificar(token)
        g.current_user = CurrentUser(id=reclamos["sub"], email=reclamos.get("email"), token=token)
        return f(*args, **kwargs)

    decorador.__dict__["requires_authentication"] = True
    return decorador


def configurar_proveedor_rol(app: Flask, proveedor: ProveedorRol) -> None:
    """Se llama en create_app: core no conoce los servicios (regla de capas)."""
    app.extensions[CLAVE_PROVEEDOR_ROL] = proveedor


def roles_required(*roles: str) -> Callable:
    """Exige un usuario autenticado cuyo rol (leido de profiles) este en `roles`."""

    def decorador(f: Callable) -> Callable:
        @wraps(f)
        def verificar_rol(*args, **kwargs):
            usuario = get_current_user()
            rol = current_app.extensions[CLAVE_PROVEEDOR_ROL](usuario.id)
            if rol not in roles:
                raise SinPermiso(MENSAJE_SIN_PERMISO)
            g.current_user = replace(usuario, rol=rol)
            return f(*args, **kwargs)

        return auth_required(verificar_rol)

    return decorador


def get_current_user() -> CurrentUser:
    usuario = g.get("current_user")
    if usuario is None:
        raise NoAutenticado(MENSAJE_FALTA_AUTENTICACION)
    return usuario


def _extraer_token(cabecera: str) -> str:
    token = cabecera.removeprefix(PREFIJO_BEARER).strip()
    if not cabecera.startswith(PREFIJO_BEARER) or not token or " " in token:
        raise NoAutenticado(MENSAJE_FALTA_AUTENTICACION)
    return token


def _decodificar(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        clave = _cliente_jwks(settings.jwks_url).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            clave,
            algorithms=ALGORITMOS_ASIMETRICOS,
            audience=AUDIENCIA,
            issuer=settings.emisor_jwt,
            leeway=TOLERANCIA_RELOJ_SEGUNDOS,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as error:
        # Nunca se registra el token, solo el motivo del rechazo.
        logger.info("JWT rechazado: %s", type(error).__name__)
        raise NoAutenticado(MENSAJE_SESION_INVALIDA) from None


@lru_cache
def _cliente_jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300)
