# =========================================================
# Autenticacion: verifica el token del usuario contra Supabase.
# TODO(HU-B-205): verificacion local del JWT y CurrentUser tipado.
# =========================================================
from functools import wraps

from flask import g, jsonify, request

from app.infrastructure.supabase_client import get_supabase


def auth_required(f):
    """Exige el header Authorization: Bearer <token>. Si es valido,
    guarda g.user_id y g.token para que la ruta los use."""

    @wraps(f)
    def decorador(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Falta el token de autenticacion"}), 401

        token = auth_header.split(" ")[1]

        try:
            usuario_response = get_supabase().auth.get_user(token)
            if not usuario_response or not usuario_response.user:
                return jsonify({"error": "Token invalido o expirado"}), 401

            g.user_id = usuario_response.user.id
            g.token = token

        except Exception:  # noqa: BLE001 - cualquier fallo del proveedor = token invalido
            return jsonify({"error": "Token invalido o expirado"}), 401

        return f(*args, **kwargs)

    return decorador
