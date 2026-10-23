# =========================================================
# /quiz/{bloque_id} (compatibilidad): delega en la evaluacion global del
# bloque (HU-B-308) y conserva la forma de respuesta anterior. Se retira
# en HU-B-312 cuando el frontend use /evaluaciones.
# =========================================================
from typing import Any

from app.core.errors import NoEncontrado
from app.repositories.base import Fila
from app.services.evaluacion_service import EvaluacionService


class QuizService:
    def __init__(self, evaluaciones: EvaluacionService) -> None:
        self._evaluaciones = evaluaciones

    def obtener_preguntas(self, bloque_id: int) -> list[Fila]:
        evaluacion = self._evaluaciones.evaluacion_de_bloque(bloque_id)
        if evaluacion is None:
            return []
        return [
            {
                "id": p["id"],
                "pregunta": p["enunciado"],
                "opciones": p["opciones"],
                "orden_index": p["orden"],
            }
            for p in self._evaluaciones.preguntas_publicas(evaluacion["id"])
        ]

    def verificar(
        self, bloque_id: int, respuestas: dict[str, Any], usuario_id: str
    ) -> dict[str, Any]:
        evaluacion = self._evaluaciones.evaluacion_de_bloque(bloque_id)
        if evaluacion is None:
            raise NoEncontrado("Este bloque no tiene preguntas")
        intento = self._evaluaciones.presentar(evaluacion["id"], usuario_id, respuestas)
        return {
            "porcentaje": intento["puntaje"],
            "correctas": intento["correctas"],
            "total": intento["total"],
            "aprobado": intento["aprobado"],
            "minimo_requerido": intento["minimo_requerido"],
            "detalle": intento["detalle"],
        }
