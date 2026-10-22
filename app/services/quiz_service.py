from typing import Any

from app.core.constants import PORCENTAJE_APROBACION, TIPO_BLOQUE
from app.core.errors import ErrorProveedor, NoEncontrado
from app.repositories.base import Fila, LectorQuiz, RepositorioProgreso


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
    def __init__(self, preguntas: LectorQuiz, progreso: RepositorioProgreso) -> None:
        self._preguntas = preguntas
        self._progreso = progreso

    def obtener_preguntas(self, bloque_id: int) -> list[Fila]:
        return self._preguntas.preguntas_publicas(bloque_id)

    def verificar(
        self, bloque_id: int, respuestas: dict[str, Any], usuario_id: str, token: str
    ) -> dict[str, Any]:
        """Califica y guarda el mejor resultado; un intento peor nunca quita la aprobacion."""
        preguntas = self._preguntas.preguntas_con_respuesta(bloque_id)
        if not preguntas:
            raise NoEncontrado("Este bloque no tiene preguntas")

        resultado = calificar(preguntas, respuestas)
        aprobado = resultado["porcentaje"] >= PORCENTAJE_APROBACION
        previo = self._resultado_previo(bloque_id, usuario_id, token)

        self._progreso.guardar(
            {
                "usuario_id": usuario_id,
                "tipo": TIPO_BLOQUE,
                "contenido_id": bloque_id,
                "porcentaje": max(resultado["porcentaje"], previo.get("porcentaje", 0)),
                "completado": aprobado or bool(previo.get("completado")),
            },
            token,
        )
        return {
            "porcentaje": resultado["porcentaje"],
            "correctas": resultado["correctas"],
            "total": resultado["total"],
            "aprobado": aprobado,
            "minimo_requerido": PORCENTAJE_APROBACION,
            "detalle": resultado["detalle"],
        }

    def _resultado_previo(self, bloque_id: int, usuario_id: str, token: str) -> Fila:
        # Igual que antes del refactor: si la consulta del previo falla,
        # se califica como primer intento en lugar de cortar la peticion.
        try:
            return self._progreso.obtener(usuario_id, TIPO_BLOQUE, bloque_id, token) or {}
        except ErrorProveedor:
            return {}
