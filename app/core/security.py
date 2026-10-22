# =========================================================
# Autenticacion: verifica el token del usuario contra Supabase.
# TODO(HU-B-205): verificacion local del JWT y CurrentUser tipado.
# =========================================================
from functools import wraps

from flask import g, request

from app.core.errors import NoAutenticado
from app.infrastructure.supabase_client import get_supabase

PREFIJO_BEARER = "Bearer "


def auth_required(f):
    """Exige el header Authorization: Bearer <token>. Si es valido,
    guarda g.user_id y g.token para que la ruta los use."""

    @wraps(f)
    def decorador(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(PREFIJO_BEARER):
            raise NoAutenticado("Falta el token de autenticacion")

        token = auth_header.split(" ")[1]
        g.user_id = _usuario_del_token(token)
        g.token = token
        return f(*args, **kwargs)

    return decorador


def _usuario_del_token(token: str) -> str:
    try:
        respuesta = get_supabase().auth.get_user(token)
    except Exception:  # noqa: BLE001 - cualquier fallo del proveedor = token invalido
        respuesta = None
    if not respuesta or not respuesta.user:
        raise NoAutenticado("Token invalido o expirado")
    return respuesta.user.id
