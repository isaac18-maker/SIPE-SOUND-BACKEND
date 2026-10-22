from app.repositories.base import Fila, LectorAcordes


class AcordeService:
    def __init__(self, lector: LectorAcordes) -> None:
        self._lector = lector

    def listar(self) -> list[Fila]:
        return self._lector.listar()
