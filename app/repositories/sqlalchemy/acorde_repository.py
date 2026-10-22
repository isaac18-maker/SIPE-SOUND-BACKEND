from sqlalchemy import select

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
