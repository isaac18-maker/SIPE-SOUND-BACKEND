# =========================================================
# Calificacion de intentos (HU-B-308). Funciones puras: sin base de datos.
# Cada tipo de pregunta tiene su estrategia (principio abierto/cerrado):
# un tipo nuevo se agrega en CALIFICADORES sin tocar calificar().
# =========================================================
from typing import Any, Protocol

from app.core.constants import TIPO_PREGUNTA_OPCION_UNICA
from app.repositories.base import Fila


class Calificador(Protocol):
    def es_correcta(self, pregunta: Fila, respuesta: Any) -> bool: ...


class CalificadorOpcionUnica:
    def es_correcta(self, pregunta: Fila, respuesta: Any) -> bool:
        # bool es subclase de int en Python: True no puede valer como indice 1.
        es_indice = isinstance(respuesta, int) and not isinstance(respuesta, bool)
        return es_indice and respuesta == pregunta["respuesta_correcta"]


CALIFICADORES: dict[str, Calificador] = {TIPO_PREGUNTA_OPCION_UNICA: CalificadorOpcionUnica()}


def calificar(
    preguntas: list[Fila], respuestas: dict[str, Any], porcentaje_aprobacion: int
) -> dict[str, Any]:
    """Una pregunta sin responder cuenta como incorrecta."""
    detalle = {}
    for pregunta in preguntas:
        pid = str(pregunta["id"])
        calificador = CALIFICADORES[pregunta.get("tipo", TIPO_PREGUNTA_OPCION_UNICA)]
        detalle[pid] = {
            "correcta": calificador.es_correcta(pregunta, respuestas.get(pid)),
            "respuesta_correcta": pregunta["respuesta_correcta"],
        }
    correctas = sum(1 for d in detalle.values() if d["correcta"])
    total = len(preguntas)
    puntaje = round(correctas * 100 / total)
    return {
        "puntaje": puntaje,
        "correctas": correctas,
        "total": total,
        "aprobado": puntaje >= porcentaje_aprobacion,
        "minimo_requerido": porcentaje_aprobacion,
        "detalle": detalle,
    }
