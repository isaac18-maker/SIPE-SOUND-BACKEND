# =========================================================
# Autenticacion: valida localmente el JWT emitido por Supabase Auth
# (firma, exp, aud e iss) sin llamar a la red en cada peticion.
# Con claves asimetricas solo se descarga el JWKS publico (cacheado).
# =========================================================
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache, wraps
from typing import Any

import jwt
from flask import g, request

from app.core.config import get_settings
from app.core.errors import NoAutenticado

logger = logging.getLogger(__name__)

PREFIJO_BEARER = "Bearer "
AUDIENCIA = "authenticated"
ALGORITMOS_ASIMETRICOS = ["ES256", "RS256"]
ALGORITMO_SECRETO = "HS256"
TOLERANCIA_RELOJ_SEGUNDOS = 10
MENSAJE_FALTA_AUTENTICACION = "Falta el token de autenticacion"
MENSAJE_SESION_INVALIDA = "Token invalido o expirado"


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    token: str


def auth_required(f: Callable) -> Callable:
    """Exige un JWT valido de Supabase y deja el usuario en get_current_user()."""

    @wraps(f)
    def decorador(*args, **kwargs):
        token = _extraer_token(request.headers.get("Authorization", ""))
        reclamos = _decodificar(token)
        g.current_user = CurrentUser(id=reclamos["sub"], email=reclamos.get("email"), token=token)
        return f(*args, **kwargs)

    return decorador


def roles_required(*roles: str) -> Callable:  # noqa: ARG001 - se usa en HU-B-304
    """Por ahora solo exige autenticacion.
    TODO(HU-B-304): cargar el rol desde profiles y responder 403 si no esta en `roles`."""

    def decorador(f: Callable) -> Callable:
        return auth_required(f)

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
        if settings.supabase_jwks_url:
            clave = _cliente_jwks(settings.supabase_jwks_url).get_signing_key_from_jwt(token).key
            algoritmos = ALGORITMOS_ASIMETRICOS
        else:
            clave = settings.supabase_jwt_secret.get_secret_value()
            algoritmos = [ALGORITMO_SECRETO]
        return jwt.decode(
            token,
            clave,
            algorithms=algoritmos,
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
