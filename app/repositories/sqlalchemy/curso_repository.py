from sqlalchemy import delete, exists, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as insert_pg
from sqlalchemy.orm import Session

from app.core.constants import ESTADO_PUBLICADO, EVALUACION_PUBLICADA
from app.models.bloque import Bloque
from app.models.curso import Curso
from app.models.curso_bloque import CursoBloque
from app.models.inscripcion import Inscripcion
from app.models.profile import Profile
from app.models.retroalimentacion import Retroalimentacion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila, filas_sql, formatear_fecha

# Avance del estudiante en cada uno de sus cursos activos (HU-B-502): UNA sentencia, sin N+1.
# La ruta de cada curso es la propia (curso_bloques) o, si no definio la suya, la global: la misma
# regla de la ruta del estudiante y del panel del docente (seguimiento_repository.CTE_RUTA).
AVANCE_DE_CURSOS = """
with mis as (
  select c.id as curso_id
  from public.inscripciones i
  join public.cursos c on c.id = i.curso_id
  where i.estudiante_id = cast(:e as uuid) and c.archivado_en is null
),
ruta as (
  select m.curso_id, cb.bloque_id from mis m
  join public.curso_bloques cb on cb.curso_id = m.curso_id
  join public.bloques b on b.id = cb.bloque_id and b.estado = :publicado
  union all
  select m.curso_id, b.id from mis m
  join public.bloques b on b.estado = :publicado
  where not exists (select 1 from public.curso_bloques cb where cb.curso_id = m.curso_id)
),
lecc as (
  select r.curso_id, l.id as leccion_id from ruta r
  join public.lecciones l on l.bloque_id = r.bloque_id and l.estado = :publicado
),
ejer as (
  select x.curso_id, e.id as ejercicio_id from lecc x
  join public.ejercicios e on e.leccion_id = x.leccion_id and e.estado = :publicado
),
evals as (
  select r.curso_id, r.bloque_id, ev.id as evaluacion_id from ruta r
  join public.evaluaciones ev on ev.bloque_id = r.bloque_id and ev.curso_id is null
    and ev.estado = :evaluacion_publicada
)
select m.curso_id,
  (select count(*) from lecc x where x.curso_id = m.curso_id)::int as lecciones_total,
  (select count(*) from lecc x
     join public.progreso_lecciones p on p.leccion_id = x.leccion_id
      and p.estudiante_id = cast(:e as uuid) and p.completado
   where x.curso_id = m.curso_id)::int as lecciones_completadas,
  (select count(*) from ejer x where x.curso_id = m.curso_id)::int as ejercicios_total,
  (select count(*) from ejer x
     join public.progreso_ejercicios p on p.ejercicio_id = x.ejercicio_id
      and p.estudiante_id = cast(:e as uuid) and p.completado
   where x.curso_id = m.curso_id)::int as ejercicios_completados,
  (select count(*) from ruta x where x.curso_id = m.curso_id)::int as bloques_total,
  (select count(distinct x.bloque_id) from evals x
   where x.curso_id = m.curso_id)::int as bloques_con_evaluacion,
  (select count(distinct x.bloque_id) from evals x
     join public.intentos_evaluacion it on it.evaluacion_id = x.evaluacion_id
      and it.estudiante_id = cast(:e as uuid) and it.aprobado
   where x.curso_id = m.curso_id)::int as bloques_aprobados,
  greatest(
    (select max(p.actualizado_en) from lecc x
       join public.progreso_lecciones p on p.leccion_id = x.leccion_id
        and p.estudiante_id = cast(:e as uuid) where x.curso_id = m.curso_id),
    (select max(p.actualizado_en) from ejer x
       join public.progreso_ejercicios p on p.ejercicio_id = x.ejercicio_id
        and p.estudiante_id = cast(:e as uuid) where x.curso_id = m.curso_id),
    (select max(it.creado_en) from evals x
       join public.intentos_evaluacion it on it.evaluacion_id = x.evaluacion_id
        and it.estudiante_id = cast(:e as uuid) where x.curso_id = m.curso_id)
  ) as ultimo_avance
from mis m
"""


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

    def tiene_inscripcion_activa(self, sesion: Session, usuario_id: str) -> bool:
        """Esta inscrito en al menos un curso activo (HU-B-414: sin curso no hay ruta)."""
        consulta = (
            select(Inscripcion.id)
            .join(Curso, Curso.id == Inscripcion.curso_id)
            .where(Inscripcion.estudiante_id == usuario_id, Curso.archivado_en.is_(None))
            .limit(1)
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

    # --- Panel docente (HU-B-310) ----------------------------------------------
    def _con_conteos(self):
        """Curso + conteo de estudiantes y de bloques de su ruta (1 consulta, sin N+1)."""
        estudiantes = (
            select(func.count())
            .where(Inscripcion.curso_id == Curso.id)
            .correlate(Curso)
            .scalar_subquery()
        )
        bloques = (
            select(func.count())
            .where(CursoBloque.curso_id == Curso.id)
            .correlate(Curso)
            .scalar_subquery()
        )
        return select(Curso, estudiantes.label("estudiantes"), bloques.label("bloques_en_ruta"))

    @staticmethod
    def _filas_con_conteos(sesion: Session, consulta) -> list[Fila]:
        return [
            {**a_fila(f.Curso), "estudiantes": f.estudiantes, "bloques_en_ruta": f.bloques_en_ruta}
            for f in sesion.execute(consulta)
        ]

    def listar_de_docente(
        self, sesion: Session, docente_id: str | None, *, archivados: bool
    ) -> list[Fila]:
        """docente_id None = administrador. Con conteo de estudiantes y de bloques (1 consulta)."""
        consulta = self._con_conteos().where(
            Curso.archivado_en.is_not(None) if archivados else Curso.archivado_en.is_(None)
        )
        if docente_id is not None:
            consulta = consulta.where(Curso.docente_id == docente_id)
        return self._filas_con_conteos(sesion, consulta.order_by(Curso.creado_en.desc()))

    def tiene_curso_activo(self, sesion: Session, docente_id: str) -> bool:
        consulta = select(
            exists().where(Curso.docente_id == docente_id, Curso.archivado_en.is_(None))
        )
        return bool(sesion.scalar(consulta))

    def quitar_docente(self, sesion: Session, curso_id: int, docente_id: str) -> Fila | None:
        """Deja el curso disponible. Solo si `docente_id` es quien lo tiene."""
        curso = sesion.scalars(
            update(Curso)
            .where(Curso.id == curso_id, Curso.docente_id == docente_id)
            .values(docente_id=None, actualizado_en=func.now())
            .returning(Curso),
            execution_options={"populate_existing": True},
        ).one_or_none()
        return a_fila(curso) if curso else None

    def ruta(self, sesion: Session, curso_id: int) -> list[Fila]:
        consulta = (
            select(CursoBloque.bloque_id, CursoBloque.orden, Bloque.titulo, Bloque.numero)
            .join(Bloque, Bloque.id == CursoBloque.bloque_id)
            .where(CursoBloque.curso_id == curso_id)
            .order_by(CursoBloque.orden)
        )
        return [dict(f._mapping) for f in sesion.execute(consulta)]

    def contar_estudiantes(self, sesion: Session, curso_id: int) -> int:
        consulta = select(func.count()).where(Inscripcion.curso_id == curso_id)
        return sesion.scalar(consulta) or 0

    def actualizar(self, sesion: Session, curso_id: int, cambios: Fila) -> Fila:
        curso = sesion.scalars(
            update(Curso).where(Curso.id == curso_id).values(**cambios).returning(Curso),
            execution_options={"populate_existing": True},
        ).one()
        return a_fila(curso)

    def retirar(self, sesion: Session, curso_id: int, estudiante_id: str) -> bool:
        """Borra solo la inscripcion: el progreso del estudiante es suyo y se conserva."""
        resultado = sesion.execute(
            delete(Inscripcion).where(
                Inscripcion.curso_id == curso_id, Inscripcion.estudiante_id == estudiante_id
            )
        )
        return resultado.rowcount > 0

    def crear_retroalimentacion(self, sesion: Session, datos: Fila) -> Fila:
        fila = sesion.scalars(
            insert(Retroalimentacion).values(**datos).returning(Retroalimentacion)
        ).one()
        return a_fila(fila)

    def marcar_leidas(self, sesion: Session, curso_id: int, estudiante_id: str) -> None:
        sesion.execute(
            update(Retroalimentacion)
            .where(
                Retroalimentacion.curso_id == curso_id,
                Retroalimentacion.estudiante_id == estudiante_id,
                Retroalimentacion.leida_en.is_(None),
            )
            .values(leida_en=func.now())
        )

    def avance_de_cursos(self, sesion: Session, estudiante_id: str) -> dict[int, Fila]:
        """curso_id -> conteos de avance del estudiante (HU-B-502). El estado se calcula aparte."""
        filas = filas_sql(
            sesion,
            AVANCE_DE_CURSOS,
            {
                "e": estudiante_id,
                "publicado": ESTADO_PUBLICADO,
                "evaluacion_publicada": EVALUACION_PUBLICADA,
            },
        )
        return {fila["curso_id"]: fila for fila in filas}

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
                Profile.apellido.label("docente_apellido"),
                Inscripcion.inscrito_en,
                sin_leer.label("retroalimentaciones_sin_leer"),
            )
            .join(Inscripcion, Inscripcion.curso_id == Curso.id)
            .outerjoin(Profile, Profile.id == Curso.docente_id)
            .where(Inscripcion.estudiante_id == estudiante_id, Curso.archivado_en.is_(None))
            .order_by(Inscripcion.inscrito_en.desc())
        )
        return [
            {**fila._mapping, "inscrito_en": formatear_fecha(fila.inscrito_en)}
            for fila in sesion.execute(consulta)
        ]
