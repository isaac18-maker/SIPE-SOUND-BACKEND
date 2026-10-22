from sqlalchemy import exists, select

from app.models.ejercicio import Ejercicio
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila


class SqlEjercicioRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            # Sin ORDER BY, igual que la consulta original a Supabase.
            return [a_fila(e) for e in sesion.scalars(select(Ejercicio))]

    def existe(self, contenido_id: int) -> bool:
        with self._abrir_sesion() as sesion:
            return bool(sesion.scalar(select(exists().where(Ejercicio.id == contenido_id))))
