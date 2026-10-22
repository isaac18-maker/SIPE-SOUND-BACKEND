from app.repositories.base import Fila
from app.repositories.supabase._comun import existe_id, publicados


class SupabaseLeccionRepository:
    def listar(self) -> list[Fila]:
        return publicados("lecciones").order("numero").execute().data

    def obtener(self, leccion_id: int) -> Fila | None:
        respuesta = publicados("lecciones").eq("id", leccion_id).maybe_single().execute()
        return respuesta.data if respuesta else None

    def existe(self, contenido_id: int) -> bool:
        return existe_id("lecciones", contenido_id)
