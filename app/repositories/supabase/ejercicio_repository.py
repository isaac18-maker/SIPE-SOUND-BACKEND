from app.repositories.base import Fila
from app.repositories.supabase._comun import existe_id, publicados


class SupabaseEjercicioRepository:
    def listar(self) -> list[Fila]:
        return publicados("ejercicios").execute().data

    def existe(self, contenido_id: int) -> bool:
        return existe_id("ejercicios", contenido_id)
