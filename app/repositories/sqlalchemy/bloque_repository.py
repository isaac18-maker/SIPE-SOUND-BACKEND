from sqlalchemy import select

from app.models.bloque import Bloque
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila


class SqlBloqueRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            bloques = sesion.scalars(select(Bloque).order_by(Bloque.orden_index))
            return [a_fila(b) for b in bloques]
