from app.repositories.base import Fila
from app.repositories.supabase._comun import publicados


class SupabaseBloqueRepository:
    def listar(self) -> list[Fila]:
        return publicados("bloques").order("orden_index").execute().data
