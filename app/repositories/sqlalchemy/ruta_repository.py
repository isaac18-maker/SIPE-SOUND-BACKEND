from sqlalchemy import and_, false, func, select
from sqlalchemy.orm import Session

from app.core.constants import ESTADO_PUBLICADO, EVALUACION_PUBLICADA
from app.models.bloque import Bloque
from app.models.curso_bloque import CursoBloque
from app.models.evaluacion import Evaluacion, IntentoEvaluacion
from app.models.leccion import Leccion
from app.models.progreso_contenido import ProgresoLeccion
from app.repositories.base import Fila

COLUMNAS_BLOQUE = (Bloque.id, Bloque.numero, Bloque.titulo, Bloque.descripcion, Bloque.nivel)


class SqlRutaRepository:
    """Consultas de la ruta de aprendizaje. Usa la sesion del servicio."""

    def bloques(self, sesion: Session, curso_id: int | None) -> list[Fila]:
        """Ruta del curso (curso_bloques) o, si no tiene, la global por orden_index.
        Solo bloques publicados."""
        if curso_id is not None:
            del_curso = (
                select(*COLUMNAS_BLOQUE)
                .join(CursoBloque, CursoBloque.bloque_id == Bloque.id)
                .where(CursoBloque.curso_id == curso_id, Bloque.estado == ESTADO_PUBLICADO)
                .order_by(CursoBloque.orden)
            )
            filas = [dict(f._mapping) for f in sesion.execute(del_curso)]
            if filas:
                return filas
        globales = (
            select(*COLUMNAS_BLOQUE)
            .where(Bloque.estado == ESTADO_PUBLICADO)
            .order_by(Bloque.orden_index)
        )
        return [dict(f._mapping) for f in sesion.execute(globales)]

    def lecciones(
        self, sesion: Session, bloque_ids: list[int], estudiante_id: str | None
    ) -> list[Fila]:
        """Lecciones publicadas de los bloques, con `completado` del estudiante."""
        completado = func.coalesce(ProgresoLeccion.completado, False) if estudiante_id else false()
        consulta = select(
            Leccion.id,
            Leccion.bloque_id,
            Leccion.numero,
            Leccion.titulo,
            Leccion.duracion_min,
            Leccion.acordes,
            completado.label("completado"),
        ).where(Leccion.bloque_id.in_(bloque_ids), Leccion.estado == ESTADO_PUBLICADO)
        if estudiante_id:
            consulta = consulta.outerjoin(
                ProgresoLeccion,
                and_(
                    ProgresoLeccion.leccion_id == Leccion.id,
                    ProgresoLeccion.estudiante_id == estudiante_id,
                ),
            )
        return [dict(f._mapping) for f in sesion.execute(consulta.order_by(Leccion.numero))]

    def evaluaciones_de_bloques(self, sesion: Session, bloque_ids: list[int]) -> dict[int, int]:
        """bloque_id -> id de su evaluacion global publicada."""
        consulta = select(Evaluacion.bloque_id, Evaluacion.id).where(
            Evaluacion.bloque_id.in_(bloque_ids),
            Evaluacion.curso_id.is_(None),
            Evaluacion.estado == EVALUACION_PUBLICADA,
        )
        return {f.bloque_id: f.id for f in sesion.execute(consulta)}

    def desempeno(
        self, sesion: Session, bloque_ids: list[int], estudiante_id: str
    ) -> dict[int, Fila]:
        """bloque_id -> mejor puntaje y si aprobo alguna vez (evaluaciones globales)."""
        consulta = (
            select(
                Evaluacion.bloque_id,
                func.max(IntentoEvaluacion.puntaje).label("mejor_puntaje"),
                func.bool_or(IntentoEvaluacion.aprobado).label("aprobado"),
            )
            .join(IntentoEvaluacion, IntentoEvaluacion.evaluacion_id == Evaluacion.id)
            .where(
                Evaluacion.bloque_id.in_(bloque_ids),
                Evaluacion.curso_id.is_(None),
                IntentoEvaluacion.estudiante_id == estudiante_id,
            )
            .group_by(Evaluacion.bloque_id)
        )
        return {
            f.bloque_id: {"mejor_puntaje": f.mejor_puntaje, "aprobado": f.aprobado}
            for f in sesion.execute(consulta)
        }
