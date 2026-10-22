from sqlalchemy import select

from app.models.quiz_pregunta import QuizPregunta
from app.repositories.base import AbrirSesion, Fila


class SqlQuizRepository:
    """Lee el quiz con la conexion del servidor: la anon key ya no puede ver
    respuesta_correcta (HU-B-313)."""

    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def preguntas_publicas(self, bloque_id: int) -> list[Fila]:
        """Sin la respuesta correcta: es lo unico que puede ver el frontend."""
        columnas = (
            QuizPregunta.id,
            QuizPregunta.pregunta,
            QuizPregunta.opciones,
            QuizPregunta.orden_index,
        )
        consulta = (
            select(*columnas)
            .where(QuizPregunta.bloque_id == bloque_id)
            .order_by(QuizPregunta.orden_index)
        )
        return self._filas(consulta)

    def preguntas_con_respuesta(self, bloque_id: int) -> list[Fila]:
        consulta = select(QuizPregunta.id, QuizPregunta.respuesta_correcta).where(
            QuizPregunta.bloque_id == bloque_id
        )
        return self._filas(consulta)

    def _filas(self, consulta) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            return [dict(fila._mapping) for fila in sesion.execute(consulta)]
