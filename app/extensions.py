# =========================================================
# Shim temporal: mantiene funcionando los imports antiguos
# (from ..extensions import supabase) mientras las rutas se
# migran a capas.
# TODO(HU-B-203): eliminar shim
# =========================================================
from app.core.config import get_settings
from app.infrastructure.supabase_client import get_supabase

SUPABASE_URL = get_settings().supabase_url
SUPABASE_KEY = get_settings().supabase_anon_key

supabase = get_supabase()
