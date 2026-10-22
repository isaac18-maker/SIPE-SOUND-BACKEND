from app.repositories.base import Fila, LectorBloques


class BloqueService:
    def __init__(self, lector: LectorBloques) -> None:
        self._lector = lector

    def listar(self) -> list[Fila]:
        return self._lector.listar()
