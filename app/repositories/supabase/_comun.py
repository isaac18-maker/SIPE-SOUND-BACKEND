from app.infrastructure.supabase_client import get_supabase


def existe_id(tabla: str, contenido_id: int) -> bool:
    respuesta = get_supabase().table(tabla).select("id").eq("id", contenido_id).execute()
    return bool(respuesta.data)
