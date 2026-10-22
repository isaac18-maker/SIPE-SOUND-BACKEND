from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila


class SupabaseBloqueRepository:
    def listar(self) -> list[Fila]:
        return get_supabase().table("bloques").select("*").order("orden_index").execute().data
