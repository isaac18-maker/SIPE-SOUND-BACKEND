# =========================================================
# Composition root: el UNICO lugar que decide que implementacion
# de repositorio recibe cada servicio (inversion de dependencias).
# Vive fuera de core/ porque depende de services y repositories.
# Todo el acceso a datos es por SQL con una sola conexion (HU-B-315).
# =========================================================
from functools import lru_cache

from sqlalchemy import exists

from app.infrastructure.database import session_scope
from app.models.bloque import Bloque
from app.models.ejercicio import Ejercicio
from app.models.evaluacion import Evaluacion
from app.models.leccion import Leccion
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.repositories.sqlalchemy.acorde_repository import SqlAcordeRepository
from app.repositories.sqlalchemy.bloque_repository import SqlBloqueRepository
from app.repositories.sqlalchemy.contenido_repository import (
    SqlCatalogoRepository,
    SqlContenidoRepository,
)
from app.repositories.sqlalchemy.curso_repository import SqlCursoRepository
from app.repositories.sqlalchemy.docente_repository import SqlDocenteRepository
from app.repositories.sqlalchemy.ejercicio_repository import SqlEjercicioRepository
from app.repositories.sqlalchemy.evaluacion_repository import SqlEvaluacionRepository
from app.repositories.sqlalchemy.gestion_evaluacion_repository import (
    SqlGestionEvaluacionRepository,
)
from app.repositories.sqlalchemy.leccion_repository import SqlLeccionRepository
from app.repositories.sqlalchemy.perfil_repository import SqlPerfilRepository
from app.repositories.sqlalchemy.progreso_repository import SqlProgresoRepository
from app.repositories.sqlalchemy.ruta_repository import SqlRutaRepository
from app.repositories.sqlalchemy.seguimiento_repository import SqlSeguimientoRepository
from app.services.acorde_service import AcordeService
from app.services.bloque_service import BloqueService
from app.services.contenido_service import ContenidoService
from app.services.curso_service import CursoService
from app.services.docente_service import DocenteService
from app.services.ejercicio_service import EjercicioService
from app.services.evaluacion_service import EvaluacionService
from app.services.gestion_evaluacion_service import GestionEvaluacionService
from app.services.leccion_service import LeccionService
from app.services.perfil_service import AdminUsuariosService, PerfilService
from app.services.progreso_service import ProgresoService
from app.services.quiz_service import QuizService
from app.services.ruta_service import RutaService


@lru_cache
def bloque_service() -> BloqueService:
    return BloqueService(SqlBloqueRepository(session_scope))


@lru_cache
def leccion_service() -> LeccionService:
    return LeccionService(SqlLeccionRepository(session_scope))


@lru_cache
def ejercicio_service() -> EjercicioService:
    return EjercicioService(SqlEjercicioRepository(session_scope))


@lru_cache
def acorde_service() -> AcordeService:
    return AcordeService(SqlAcordeRepository(session_scope))


@lru_cache
def progreso_service() -> ProgresoService:
    return ProgresoService(
        session_scope,
        SqlProgresoRepository(),
        evaluaciones=SqlEvaluacionRepository(),
        lecciones=SqlLeccionRepository(session_scope),
        ejercicios=SqlEjercicioRepository(session_scope),
    )


@lru_cache
def quiz_service() -> QuizService:
    return QuizService(evaluacion_service())


@lru_cache
def ruta_service() -> RutaService:
    return RutaService(session_scope, SqlRutaRepository(), SqlCursoRepository())


@lru_cache
def evaluacion_service() -> EvaluacionService:
    return EvaluacionService(
        session_scope, SqlEvaluacionRepository(), SqlCursoRepository(), ruta_service()
    )


@lru_cache
def perfil_service() -> PerfilService:
    return PerfilService(session_scope, SqlPerfilRepository())


@lru_cache
def admin_usuarios_service() -> AdminUsuariosService:
    return AdminUsuariosService(session_scope, SqlPerfilRepository())


@lru_cache
def curso_service() -> CursoService:
    return CursoService(
        session_scope, SqlCursoRepository(), SqlSeguimientoRepository(), ruta_service()
    )


@lru_cache
def docente_service() -> DocenteService:
    return DocenteService(session_scope, SqlDocenteRepository())


def rol_de_usuario(usuario_id: str) -> str | None:
    return perfil_service().rol_de(usuario_id)


# --- Contenido editable (HU-B-309): un servicio generico configurado por tipo ---
@lru_cache
def leccion_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Leccion,
        columna_texto=Leccion.titulo,
        filtros=("estado", "bloque_id"),
        en_uso=lambda i: exists().where(ProgresoLeccion.leccion_id == i),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="la lección",
        con_autor=True,
        referencias={"bloque_id": "bloques"},
        en_uso="La lección tiene avance de estudiantes. Archívala para ocultarla sin perderlo.",
    )


@lru_cache
def ejercicio_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Ejercicio,
        columna_texto=Ejercicio.nombre,
        filtros=("estado", "leccion_id"),
        en_uso=lambda i: exists().where(ProgresoEjercicio.ejercicio_id == i),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="el ejercicio",
        con_autor=True,
        referencias={"leccion_id": "lecciones"},
        en_uso="El ejercicio tiene avance de estudiantes. Archívalo para ocultarlo sin perderlo.",
    )


@lru_cache
def bloque_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Bloque,
        columna_texto=Bloque.titulo,
        filtros=("estado",),
        en_uso=lambda i: (
            exists().where(Leccion.bloque_id == i) | exists().where(Evaluacion.bloque_id == i)
        ),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="el bloque",
        con_autor=False,
        referencias={},
        en_uso="El bloque tiene lecciones o evaluaciones. Archívalo en lugar de borrarlo.",
    )


@lru_cache
def gestion_evaluacion_service() -> GestionEvaluacionService:
    return GestionEvaluacionService(
        session_scope, SqlGestionEvaluacionRepository(), curso_service()
    )
