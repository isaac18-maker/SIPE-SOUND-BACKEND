# =========================================================
# Composition root: el UNICO lugar que decide que implementacion
# de repositorio recibe cada servicio (inversion de dependencias).
# Vive fuera de core/ porque depende de services y repositories.
# Todo el acceso a datos es por SQL con una sola conexion (HU-B-315).
# =========================================================
from functools import lru_cache

from app.infrastructure.database import session_scope
from app.repositories.sqlalchemy.acorde_repository import SqlAcordeRepository
from app.repositories.sqlalchemy.bloque_repository import SqlBloqueRepository
from app.repositories.sqlalchemy.curso_repository import SqlCursoRepository
from app.repositories.sqlalchemy.ejercicio_repository import SqlEjercicioRepository
from app.repositories.sqlalchemy.leccion_repository import SqlLeccionRepository
from app.repositories.sqlalchemy.perfil_repository import SqlPerfilRepository
from app.repositories.sqlalchemy.progreso_bloques_repository import SqlProgresoBloquesRepository
from app.repositories.sqlalchemy.progreso_repository import SqlProgresoRepository
from app.repositories.sqlalchemy.quiz_repository import SqlQuizRepository
from app.services.acorde_service import AcordeService
from app.services.bloque_service import BloqueService
from app.services.curso_service import CursoService
from app.services.ejercicio_service import EjercicioService
from app.services.leccion_service import LeccionService
from app.services.perfil_service import AdminUsuariosService, PerfilService
from app.services.progreso_service import ProgresoService
from app.services.quiz_service import QuizService


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
        progreso_bloques=SqlProgresoBloquesRepository(session_scope),
        lecciones=SqlLeccionRepository(session_scope),
        ejercicios=SqlEjercicioRepository(session_scope),
    )


@lru_cache
def quiz_service() -> QuizService:
    return QuizService(
        SqlQuizRepository(session_scope), SqlProgresoBloquesRepository(session_scope)
    )


@lru_cache
def perfil_service() -> PerfilService:
    return PerfilService(session_scope, SqlPerfilRepository())


@lru_cache
def admin_usuarios_service() -> AdminUsuariosService:
    return AdminUsuariosService(session_scope, SqlPerfilRepository())


@lru_cache
def curso_service() -> CursoService:
    return CursoService(session_scope, SqlCursoRepository())


def rol_de_usuario(usuario_id: str) -> str | None:
    return perfil_service().rol_de(usuario_id)
