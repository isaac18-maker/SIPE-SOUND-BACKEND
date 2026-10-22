from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila
from app.repositories.supabase._comun import existe_id


class SupabaseLeccionRepository:
    def listar(self) -> list[Fila]:
        return get_supabase().table("lecciones").select("*").order("numero").execute().data

    def obtener(self, leccion_id: int) -> Fila | None:
        consulta = get_supabase().table("lecciones").select("*").eq("id", leccion_id)
        respuesta = consulta.maybe_single().execute()
        return respuesta.data if respuesta else None

    def existe(self, contenido_id: int) -> bool:
        return existe_id("lecciones", contenido_id)
