from app.repositories.base import Fila, LectorEjercicios


class EjercicioService:
    def __init__(self, lector: LectorEjercicios) -> None:
        self._lector = lector

    def listar(self) -> list[Fila]:
        return self._lector.listar()
