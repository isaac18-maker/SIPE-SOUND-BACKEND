# =========================================================
# Cliente de Supabase compartido. Se crea la primera vez que
# se pide, no al importar el modulo.
# =========================================================
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
