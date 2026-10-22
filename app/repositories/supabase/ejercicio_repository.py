from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila
from app.repositories.supabase._comun import existe_id


class SupabaseEjercicioRepository:
    def listar(self) -> list[Fila]:
        return get_supabase().table("ejercicios").select("*").execute().data

    def existe(self, contenido_id: int) -> bool:
        return existe_id("ejercicios", contenido_id)
