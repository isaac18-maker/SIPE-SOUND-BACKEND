from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as insert_pg
from sqlalchemy.orm import Session

from app.core.constants import ESTADO_PUBLICADO
from app.models.bloque import Bloque
from app.models.curso import Curso
from app.models.curso_bloque import CursoBloque
from app.models.inscripcion import Inscripcion
from app.models.profile import Profile
from app.models.retroalimentacion import Retroalimentacion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila, formatear_fecha


class SqlCursoRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def crear(self, sesion: Session, datos: Fila) -> Fila:
        curso = sesion.scalars(insert(Curso).values(**datos).returning(Curso)).one()
        return a_fila(curso)

    def obtener(self, sesion: Session, curso_id: int, *, bloquear: bool = False) -> Fila | None:
        curso = sesion.get(Curso, curso_id, with_for_update=bloquear)
        return a_fila(curso) if curso else None

    def obtener_activo_por_codigo(self, sesion: Session, codigo: str) -> Fila | None:
        consulta = select(Curso).where(
            Curso.codigo_invitacion == codigo, Curso.archivado_en.is_(None)
        )
        curso = sesion.scalar(consulta)
        return a_fila(curso) if curso else None

    def inscribir(self, sesion: Session, curso_id: int, estudiante_id: str) -> None:
        # Idempotente: unirse dos veces al mismo curso no duplica ni falla.
        sesion.execute(
            insert_pg(Inscripcion)
            .values(curso_id=curso_id, estudiante_id=estudiante_id)
            .on_conflict_do_nothing(index_elements=["curso_id", "estudiante_id"])
        )

    def archivar(self, sesion: Session, curso_id: int) -> Fila:
        curso = sesion.scalars(
            update(Curso)
            .where(Curso.id == curso_id)
            .values(archivado_en=func.coalesce(Curso.archivado_en, func.now()))
            .returning(Curso),
            execution_options={"populate_existing": True},
        ).one()
        return a_fila(curso)

    def puede_ver(self, sesion: Session, curso_id: int, usuario_id: str) -> bool:
        """Curso activo donde el usuario esta inscrito o es el docente."""
        inscrito = (
            select(Inscripcion.id)
            .where(Inscripcion.curso_id == Curso.id, Inscripcion.estudiante_id == usuario_id)
            .exists()
        )
        consulta = select(Curso.id).where(
            Curso.id == curso_id,
            Curso.archivado_en.is_(None),
            (Curso.docente_id == usuario_id) | inscrito,
        )
        return sesion.scalar(consulta) is not None

    def bloques_publicados(self, sesion: Session, bloque_ids: set[int]) -> set[int]:
        consulta = select(Bloque.id).where(
            Bloque.id.in_(bloque_ids), Bloque.estado == ESTADO_PUBLICADO
        )
        return set(sesion.scalars(consulta))

    def reemplazar_ruta(self, sesion: Session, curso_id: int, ruta: list[tuple[int, int]]) -> None:
        sesion.execute(delete(CursoBloque).where(CursoBloque.curso_id == curso_id))
        if ruta:
            sesion.execute(
                insert(CursoBloque),
                [{"curso_id": curso_id, "bloque_id": b, "orden": o} for b, o in ruta],
            )

    def cursos_de_estudiante(self, sesion: Session, estudiante_id: str) -> list[Fila]:
        """Una sola consulta: curso + nombre del docente + comentarios sin leer."""
        sin_leer = (
            select(func.count())
            .where(
                Retroalimentacion.curso_id == Curso.id,
                Retroalimentacion.estudiante_id == estudiante_id,
                Retroalimentacion.leida_en.is_(None),
            )
            .scalar_subquery()
        )
        consulta = (
            select(
                Curso.id,
                Curso.nombre,
                Curso.descripcion,
                Curso.nivel,
                Profile.nombre.label("docente_nombre"),
                Inscripcion.inscrito_en,
                sin_leer.label("retroalimentaciones_sin_leer"),
            )
            .join(Inscripcion, Inscripcion.curso_id == Curso.id)
            .join(Profile, Profile.id == Curso.docente_id)
            .where(Inscripcion.estudiante_id == estudiante_id, Curso.archivado_en.is_(None))
            .order_by(Inscripcion.inscrito_en.desc())
        )
        return [
            {**fila._mapping, "inscrito_en": formatear_fecha(fila.inscrito_en)}
            for fila in sesion.execute(consulta)
        ]
