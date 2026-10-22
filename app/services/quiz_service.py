from typing import Any

from app.core.constants import PORCENTAJE_APROBACION
from app.core.errors import NoEncontrado
from app.repositories.base import Fila, LectorQuiz, RepositorioProgresoBloques


def calificar(preguntas: list[Fila], respuestas: dict[str, Any]) -> dict[str, Any]:
    """Funcion pura: compara las respuestas elegidas con las correctas."""
    detalle = {}
    for pregunta in preguntas:
        pid = str(pregunta["id"])
        es_correcta = respuestas.get(pid) == pregunta["respuesta_correcta"]
        detalle[pid] = {
            "correcta": es_correcta,
            "respuesta_correcta": pregunta["respuesta_correcta"],
        }
    correctas = sum(1 for d in detalle.values() if d["correcta"])
    return {
        "correctas": correctas,
        "total": len(preguntas),
        "porcentaje": round((correctas / len(preguntas)) * 100),
        "detalle": detalle,
    }


class QuizService:
    def __init__(self, preguntas: LectorQuiz, progreso: RepositorioProgresoBloques) -> None:
        self._preguntas = preguntas
        self._progreso = progreso

    def obtener_preguntas(self, bloque_id: int) -> list[Fila]:
        return self._preguntas.preguntas_publicas(bloque_id)

    def verificar(
        self, bloque_id: int, respuestas: dict[str, Any], usuario_id: str
    ) -> dict[str, Any]:
        """Califica y guarda el resultado. El repositorio conserva el mejor puntaje y
        un intento peor nunca quita la aprobacion."""
        preguntas = self._preguntas.preguntas_con_respuesta(bloque_id)
        if not preguntas:
            raise NoEncontrado("Este bloque no tiene preguntas")

        resultado = calificar(preguntas, respuestas)
        aprobado = resultado["porcentaje"] >= PORCENTAJE_APROBACION
        self._progreso.registrar(
            usuario_id, bloque_id, porcentaje=resultado["porcentaje"], aprobado=aprobado
        )
        return {
            "porcentaje": resultado["porcentaje"],
            "correctas": resultado["correctas"],
            "total": resultado["total"],
            "aprobado": aprobado,
            "minimo_requerido": PORCENTAJE_APROBACION,
            "detalle": resultado["detalle"],
        }
