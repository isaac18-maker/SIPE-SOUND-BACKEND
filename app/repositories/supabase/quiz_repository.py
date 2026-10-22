from app.infrastructure.supabase_client import get_supabase
from app.repositories.base import Fila


class SupabaseQuizRepository:
    def preguntas_publicas(self, bloque_id: int) -> list[Fila]:
        """Sin la respuesta correcta: es lo unico que puede ver el frontend."""
        return _preguntas(bloque_id, "id, pregunta, opciones, orden_index", ordenar=True)

    def preguntas_con_respuesta(self, bloque_id: int) -> list[Fila]:
        return _preguntas(bloque_id, "id, respuesta_correcta", ordenar=False)


def _preguntas(bloque_id: int, columnas: str, *, ordenar: bool) -> list[Fila]:
    consulta = get_supabase().table("quiz_preguntas").select(columnas).eq("bloque_id", bloque_id)
    if ordenar:
        consulta = consulta.order("orden_index")
    return consulta.execute().data
