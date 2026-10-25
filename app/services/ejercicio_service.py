from app.core.avance import estado_de_avance
from app.repositories.base import Fila, LectorEjercicios


def mi_progreso(progreso: Fila | None) -> Fila:
    """El avance del estudiante en un ejercicio (HU-B-501): finalizado si lo completo, en_curso
    si hay un registro (por ejemplo un BPM guardado) sin completar y sin_iniciar si no hay fila."""
    if progreso is None:
        return {
            "estado": estado_de_avance(hay_registro=False, completo=False),
            "mejor_bpm": None,
            "ultimo_registro": None,
        }
    return {
        "estado": estado_de_avance(hay_registro=True, completo=bool(progreso["completado"])),
        "mejor_bpm": progreso["mejor_bpm"],
        "ultimo_registro": progreso["ultimo_registro"],
    }


class EjercicioService:
    def __init__(self, lector: LectorEjercicios) -> None:
        self._lector = lector

    def listar(
        self,
        *,
        estudiante_id: str | None = None,
        estado: str | None = None,
        leccion_id: int | None = None,
    ) -> list[Fila]:
        """Sin sesion es el catalogo de siempre (sin mi_progreso y sin filtro de estado)."""
        filas = self._lector.listar(estudiante_id=estudiante_id, leccion_id=leccion_id)
        if estudiante_id is None:
            return filas
        con_progreso = [
            {
                **{k: v for k, v in f.items() if k != "progreso"},
                "mi_progreso": mi_progreso(f["progreso"]),
            }
            for f in filas
        ]
        if estado is None:
            return con_progreso
        return [f for f in con_progreso if f["mi_progreso"]["estado"] == estado]
