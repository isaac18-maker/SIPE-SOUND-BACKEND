from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila


class SupabaseAcordeRepository:
    def listar(self) -> list[Fila]:
        return get_supabase().table("acordes").select("*").execute().data
