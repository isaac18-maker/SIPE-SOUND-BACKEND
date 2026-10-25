from sqlalchemy import and_, exists, select

from app.core.constants import ESTADO_PUBLICADO
from app.models.ejercicio import Ejercicio
from app.models.progreso_contenido import ProgresoEjercicio
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import AbrirSesion, a_fila, formatear_fecha


class SqlEjercicioRepository:
    def __init__(self, abrir_sesion: AbrirSesion) -> None:
        self._abrir_sesion = abrir_sesion

    def listar(
        self, *, estudiante_id: str | None = None, leccion_id: int | None = None
    ) -> list[Fila]:
        """Ejercicios publicados. Con `estudiante_id`, cada fila trae `progreso` (la fila de
        progreso_ejercicios del estudiante o None) en la MISMA consulta (LEFT JOIN, sin N+1)."""
        with self._abrir_sesion() as sesion:
            consulta = select(Ejercicio).where(Ejercicio.estado == ESTADO_PUBLICADO)
            if leccion_id is not None:
                consulta = consulta.where(Ejercicio.leccion_id == leccion_id)
            if estudiante_id is None:
                return [a_fila(e) for e in sesion.scalars(consulta.order_by(Ejercicio.id))]
            con_progreso = (
                select(Ejercicio, ProgresoEjercicio)
                .outerjoin(
                    ProgresoEjercicio,
                    and_(
                        ProgresoEjercicio.ejercicio_id == Ejercicio.id,
                        ProgresoEjercicio.estudiante_id == estudiante_id,
                    ),
                )
                .where(Ejercicio.estado == ESTADO_PUBLICADO)
                .order_by(Ejercicio.id)
            )
            if leccion_id is not None:
                con_progreso = con_progreso.where(Ejercicio.leccion_id == leccion_id)
            return [
                {**a_fila(e), "progreso": _progreso(p)} for e, p in sesion.execute(con_progreso)
            ]

    def existe(self, contenido_id: int) -> bool:
        with self._abrir_sesion() as sesion:
            condicion = (Ejercicio.id == contenido_id) & (Ejercicio.estado == ESTADO_PUBLICADO)
            return bool(sesion.scalar(select(exists().where(condicion))))


def _progreso(fila: ProgresoEjercicio | None) -> Fila | None:
    if fila is None:
        return None
    return {
        "completado": fila.completado,
        "mejor_bpm": fila.mejor_bpm,
        "ultimo_registro": formatear_fecha(fila.actualizado_en),
    }
