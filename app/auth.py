# =========================================================
# Autenticacion: verifica el token del usuario y expone un
# helper para consultar Supabase respetando RLS.
# =========================================================
from functools import wraps
import requests
from flask import request, jsonify, g

from .extensions import supabase, SUPABASE_URL, SUPABASE_KEY


def supabase_rest(method, tabla, token, params=None, json_body=None):
    """Peticion directa a la API REST de Supabase, usando el token
    del usuario (no la anon key) para que RLS reconozca auth.uid()."""
    url = f"{SUPABASE_URL}/rest/v1/{tabla}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if method == "POST":
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

    return requests.request(method, url, headers=headers, params=params, json=json_body)


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
            usuario_response = supabase.auth.get_user(token)
            if not usuario_response or not usuario_response.user:
                return jsonify({"error": "Token invalido o expirado"}), 401

            g.user_id = usuario_response.user.id
            g.token = token

        except Exception:
            return jsonify({"error": "Token invalido o expirado"}), 401

        return f(*args, **kwargs)

    return decorador
