from typing import Protocol

from app.core.errors import NoEncontrado, ValidacionError
from app.core.youtube import VideoInvalido, extraer_video
from app.repositories.base import Fila, LectorAcordes


class EscritorVideoAcordes(Protocol):
    """Lo cumple SqlAcordeRepository."""

    def asignar_video(
        self, acorde_id: int, youtube_id: str | None, inicio_seg: int | None
    ) -> Fila | None: ...


class AcordeService:
    def __init__(self, lector: LectorAcordes, escritor: EscritorVideoAcordes | None = None) -> None:
        self._lector = lector
        self._escritor = escritor

    def listar(self) -> list[Fila]:
        return self._lector.listar()

    def asignar_video(self, acorde_id: int, video_url: str, inicio_seg: int | None = None) -> Fila:
        """El catalogo de acordes es global: solo el administrador llega aqui. Se guarda el id de
        YouTube; `inicio_seg`, si viene, gana sobre el t= de la URL."""
        try:
            video_id, inicio_url = extraer_video(video_url)
        except VideoInvalido as error:
            raise ValidacionError(str(error)) from None
        inicio = inicio_seg if inicio_seg is not None else inicio_url
        return self._con_video(acorde_id, video_id, inicio)

    def quitar_video(self, acorde_id: int) -> Fila:
        return self._con_video(acorde_id, None, None)

    def _con_video(self, acorde_id: int, video_id: str | None, inicio: int | None) -> Fila:
        acorde = self._escritor.asignar_video(acorde_id, video_id, inicio)
        if acorde is None:
            raise NoEncontrado(f"No existe el acorde {acorde_id}")
        return acorde
