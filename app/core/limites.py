# =========================================================
# Limites de peticiones (proteccion contra fuerza bruta).
# Almacenamiento en memoria: vale por proceso; con varios procesos
# o servidores habra que usar Redis (storage_uri) — ver HU-B-307.
# =========================================================
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.core.security import get_current_user

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def por_usuario() -> str:
    """Clave del limite: el usuario autenticado (no la IP, que comparten los colegios)."""
    return get_current_user().id


def configurar_limites(app: Flask) -> None:
    limiter.init_app(app)
