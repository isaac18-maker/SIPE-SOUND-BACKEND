from sqlalchemy import select, update

from app.models.acorde import Acorde
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila


class SqlAcordeRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            # Sin ORDER BY, igual que la consulta original a Supabase.
            return [a_fila(a) for a in sesion.scalars(select(Acorde))]

    def asignar_video(
        self, acorde_id: int, youtube_id: str | None, inicio_seg: int | None
    ) -> Fila | None:
        """youtube_id None quita el video. Devuelve el acorde o None si no existe."""
        with self._abrir_sesion() as sesion:
            acorde = sesion.scalars(
                update(Acorde)
                .where(Acorde.id == acorde_id)
                .values(video_youtube_id=youtube_id, video_inicio_seg=inicio_seg)
                .returning(Acorde),
                execution_options={"populate_existing": True},
            ).one_or_none()
            return a_fila(acorde) if acorde else None
