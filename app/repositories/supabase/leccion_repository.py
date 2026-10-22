from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila
from app.repositories.supabase._comun import existe_id


class SupabaseLeccionRepository:
    def listar(self) -> list[Fila]:
        return get_supabase().table("lecciones").select("*").order("numero").execute().data

    def obtener(self, leccion_id: int) -> Fila | None:
        # .single() lanza una excepcion si no hay filas (hoy responde 500).
        # TODO(HU-B-204): usar maybe_single() para devolver None y responder 404.
        consulta = get_supabase().table("lecciones").select("*").eq("id", leccion_id)
        return consulta.single().execute().data

    def existe(self, contenido_id: int) -> bool:
        return existe_id("lecciones", contenido_id)
