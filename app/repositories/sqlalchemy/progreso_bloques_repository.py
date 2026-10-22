from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.constants import TIPO_BLOQUE
from app.models.progreso import Progreso
from app.repositories.base import AbrirSesion, Fila
from app.repositories.sqlalchemy._comun import a_fila


class SqlProgresoBloquesRepository:
    """Resultado de los quizzes por bloque en la tabla `progreso` (hasta HU-B-308).
    El usuario sale siempre del token verificado, nunca del cliente."""

    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(self, usuario_id: str) -> list[Fila]:
        consulta = select(Progreso).where(
            Progreso.usuario_id == usuario_id, Progreso.tipo == TIPO_BLOQUE
        )
        with self._abrir_sesion() as sesion:
            return [a_fila(p) for p in sesion.scalars(consulta)]

    def registrar(
        self, usuario_id: str, bloque_id: int, *, porcentaje: int, aprobado: bool
    ) -> Fila:
        """Regla aplicada atomicamente: se guarda el mejor puntaje y un bloque
        aprobado no deja de estarlo por un intento peor."""
        nuevo = insert(Progreso).values(
            usuario_id=usuario_id,
            tipo=TIPO_BLOQUE,
            contenido_id=bloque_id,
            porcentaje=porcentaje,
            completado=aprobado,
        )
        upsert = nuevo.on_conflict_do_update(
            index_elements=[Progreso.usuario_id, Progreso.tipo, Progreso.contenido_id],
            set_={
                "porcentaje": func.greatest(Progreso.porcentaje, nuevo.excluded.porcentaje),
                "completado": func.coalesce(Progreso.completado, False) | nuevo.excluded.completado,
                "actualizado_en": func.now(),
            },
        ).returning(Progreso)
        with self._abrir_sesion() as sesion:
            fila = sesion.scalars(upsert, execution_options={"populate_existing": True}).one()
            return a_fila(fila)
