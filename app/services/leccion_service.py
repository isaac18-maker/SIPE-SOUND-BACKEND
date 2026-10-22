from app.core.errors import NoEncontrado
from app.repositories.base import Fila, LectorLecciones


class LeccionService:
    def __init__(self, lector: LectorLecciones) -> None:
        self._lector = lector

    def listar(self) -> list[Fila]:
        return self._lector.listar()

    def obtener(self, leccion_id: int) -> Fila:
        leccion = self._lector.obtener(leccion_id)
        if leccion is None:
            raise NoEncontrado(f"No existe leccion con id {leccion_id}")
        return leccion
