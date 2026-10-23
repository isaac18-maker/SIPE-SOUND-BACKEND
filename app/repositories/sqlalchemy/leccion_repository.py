from sqlalchemy import exists, select

from app.core.constants import ESTADO_PUBLICADO
from app.models.leccion import Leccion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila


class SqlLeccionRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            lecciones = sesion.scalars(_publicadas().order_by(Leccion.numero))
            return [a_fila(leccion) for leccion in lecciones]

    def obtener(self, leccion_id: int) -> Fila | None:
        with self._abrir_sesion() as sesion:
            leccion = sesion.scalar(_publicadas().where(Leccion.id == leccion_id))
            return a_fila(leccion) if leccion else None

    def existe(self, contenido_id: int) -> bool:
        with self._abrir_sesion() as sesion:
            condicion = (Leccion.id == contenido_id) & (Leccion.estado == ESTADO_PUBLICADO)
            return bool(sesion.scalar(select(exists().where(condicion))))


def _publicadas():
    """Catalogo publico: solo lecciones publicadas (HU-B-306)."""
    return select(Leccion).where(Leccion.estado == ESTADO_PUBLICADO)
