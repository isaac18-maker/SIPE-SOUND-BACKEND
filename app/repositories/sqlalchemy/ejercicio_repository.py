from sqlalchemy import exists, select

from app.core.constants import ESTADO_PUBLICADO
from app.models.ejercicio import Ejercicio
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila


class SqlEjercicioRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            # Sin ORDER BY, igual que la consulta original a Supabase.
            publicados = select(Ejercicio).where(Ejercicio.estado == ESTADO_PUBLICADO)
            return [a_fila(e) for e in sesion.scalars(publicados)]

    def existe(self, contenido_id: int) -> bool:
        with self._abrir_sesion() as sesion:
            condicion = (Ejercicio.id == contenido_id) & (Ejercicio.estado == ESTADO_PUBLICADO)
            return bool(sesion.scalar(select(exists().where(condicion))))
