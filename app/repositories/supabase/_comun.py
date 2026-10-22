from app.core.constants import ESTADO_PUBLICADO
from app.infrastructure.supabase_client import get_supabase


def publicados(tabla: str):
    """Consulta base del catalogo publico: solo contenido publicado (HU-B-306)."""
    return get_supabase().table(tabla).select("*").eq("estado", ESTADO_PUBLICADO)


def existe_id(tabla: str, contenido_id: int) -> bool:
    respuesta = (
        get_supabase()
        .table(tabla)
        .select("id")
        .eq("id", contenido_id)
        .eq("estado", ESTADO_PUBLICADO)
        .execute()
    )
    return bool(respuesta.data)
