from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.core.constants import EVALUACION_PUBLICADA
from app.models.evaluacion import Evaluacion, IntentoEvaluacion, PreguntaEvaluacion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila, formatear_fecha

COLUMNAS_PUBLICAS = (
    PreguntaEvaluacion.id,
    PreguntaEvaluacion.enunciado,
    PreguntaEvaluacion.opciones,
    PreguntaEvaluacion.orden,
)


class SqlEvaluacionRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def obtener(self, sesion: Session, evaluacion_id: int) -> Fila | None:
        evaluacion = sesion.get(Evaluacion, evaluacion_id)
        return a_fila(evaluacion) if evaluacion else None

    def de_bloque(self, sesion: Session, bloque_id: int) -> Fila | None:
        """La evaluacion global publicada del bloque (la que lo desbloquea)."""
        consulta = select(Evaluacion).where(
            Evaluacion.bloque_id == bloque_id,
            Evaluacion.curso_id.is_(None),
            Evaluacion.estado == EVALUACION_PUBLICADA,
        )
        evaluacion = sesion.scalar(consulta)
        return a_fila(evaluacion) if evaluacion else None

    def preguntas(self, sesion: Session, evaluacion_id: int, *, con_respuesta: bool) -> list[Fila]:
        """Sin `con_respuesta` nunca sale respuesta_correcta (vista del estudiante)."""
        columnas = (
            (*COLUMNAS_PUBLICAS, PreguntaEvaluacion.respuesta_correcta)
            if con_respuesta
            else COLUMNAS_PUBLICAS
        )
        consulta = (
            select(*columnas)
            .where(PreguntaEvaluacion.evaluacion_id == evaluacion_id)
            .order_by(PreguntaEvaluacion.orden)
        )
        return [dict(f._mapping) for f in sesion.execute(consulta)]

    def bloquear_intentos(self, sesion: Session, evaluacion_id: int, estudiante_id: str) -> None:
        """Serializa los envios de UN estudiante a UNA evaluacion hasta el commit: dos
        envios simultaneos no pueden superar intentos_max."""
        sesion.execute(
            text("select pg_advisory_xact_lock(:evaluacion, hashtext(:estudiante))"),
            {"evaluacion": evaluacion_id, "estudiante": estudiante_id},
        )

    def contar_intentos(self, sesion: Session, evaluacion_id: int, estudiante_id: str) -> int:
        consulta = select(func.count()).where(
            IntentoEvaluacion.evaluacion_id == evaluacion_id,
            IntentoEvaluacion.estudiante_id == estudiante_id,
        )
        return sesion.scalar(consulta) or 0

    def registrar_intento(self, sesion: Session, datos: Fila) -> Fila:
        intento = sesion.scalars(
            insert(IntentoEvaluacion).values(**datos).returning(IntentoEvaluacion)
        ).one()
        return a_fila(intento)

    def intentos(self, sesion: Session, evaluacion_id: int, estudiante_id: str) -> list[Fila]:
        consulta = (
            select(IntentoEvaluacion)
            .where(
                IntentoEvaluacion.evaluacion_id == evaluacion_id,
                IntentoEvaluacion.estudiante_id == estudiante_id,
            )
            .order_by(IntentoEvaluacion.creado_en.desc())
        )
        return [a_fila(i) for i in sesion.scalars(consulta)]

    def bloques_aprobados(self, sesion: Session, estudiante_id: str) -> list[Fila]:
        """Bloques con algun intento aprobado en su evaluacion global (cualquier estado)."""
        consulta = (
            select(Evaluacion.bloque_id, func.max(IntentoEvaluacion.creado_en).label("fecha"))
            .join(IntentoEvaluacion, IntentoEvaluacion.evaluacion_id == Evaluacion.id)
            .where(
                IntentoEvaluacion.estudiante_id == estudiante_id,
                IntentoEvaluacion.aprobado.is_(True),
                Evaluacion.curso_id.is_(None),
                Evaluacion.bloque_id.is_not(None),
            )
            .group_by(Evaluacion.bloque_id)
        )
        return [
            {"bloque_id": f.bloque_id, "actualizado_en": formatear_fecha(f.fecha)}
            for f in sesion.execute(consulta)
        ]
