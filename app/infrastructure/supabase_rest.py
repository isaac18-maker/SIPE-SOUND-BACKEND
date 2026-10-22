# =========================================================
# Peticion directa a la API REST de Supabase con el token del
# usuario (no la anon key) para que RLS reconozca auth.uid().
# TODO(HU-B-312): se retira cuando el acceso a datos sea SQLAlchemy.
# =========================================================
from typing import Any

import requests

from app.core.config import get_settings

TIMEOUT_SEGUNDOS = 15


def supabase_rest(
    method: str,
    tabla: str,
    token: str,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> requests.Response:
    settings = get_settings()
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if method == "POST":
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

    return requests.request(
        method,
        f"{settings.supabase_url}/rest/v1/{tabla}",
        headers=headers,
        params=params,
        json=json_body,
        timeout=TIMEOUT_SEGUNDOS,
    )
