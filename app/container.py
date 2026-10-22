# =========================================================
# Composition root: el UNICO lugar que decide que implementacion
# de repositorio recibe cada servicio (inversion de dependencias).
# Vive fuera de core/ porque depende de services y repositories.
# DATA_BACKEND elige entre Supabase (REST) y SQLAlchemy; los
# servicios no cambian (sustitucion de Liskov).
# =========================================================
from functools import lru_cache

from app.core.config import get_settings
from app.infrastructure.database import session_scope
from app.repositories.base import LectorAcordes, LectorBloques, LectorEjercicios, LectorLecciones
from app.repositories.sqlalchemy.acorde_repository import SqlAcordeRepository
from app.repositories.sqlalchemy.bloque_repository import SqlBloqueRepository
from app.repositories.sqlalchemy.ejercicio_repository import SqlEjercicioRepository
from app.repositories.sqlalchemy.leccion_repository import SqlLeccionRepository
from app.repositories.sqlalchemy.perfil_repository import SqlPerfilRepository
from app.repositories.sqlalchemy.progreso_repository import SqlProgresoRepository
from app.repositories.sqlalchemy.quiz_repository import SqlQuizRepository
from app.repositories.supabase.acorde_repository import SupabaseAcordeRepository
from app.repositories.supabase.bloque_repository import SupabaseBloqueRepository
from app.repositories.supabase.ejercicio_repository import SupabaseEjercicioRepository
from app.repositories.supabase.leccion_repository import SupabaseLeccionRepository
from app.repositories.supabase.progreso_repository import SupabaseProgresoRepository
from app.services.acorde_service import AcordeService
from app.services.bloque_service import BloqueService
from app.services.ejercicio_service import EjercicioService
from app.services.leccion_service import LeccionService
from app.services.perfil_service import AdminUsuariosService, PerfilService
from app.services.progreso_service import ProgresoService
from app.services.quiz_service import QuizService


def _usa_sql() -> bool:
    return get_settings().data_backend == "sql"


def _repo_bloques() -> LectorBloques:
    return SqlBloqueRepository(session_scope) if _usa_sql() else SupabaseBloqueRepository()


def _repo_lecciones() -> LectorLecciones:
    return SqlLeccionRepository(session_scope) if _usa_sql() else SupabaseLeccionRepository()


def _repo_ejercicios() -> LectorEjercicios:
    return SqlEjercicioRepository(session_scope) if _usa_sql() else SupabaseEjercicioRepository()


def _repo_acordes() -> LectorAcordes:
    return SqlAcordeRepository(session_scope) if _usa_sql() else SupabaseAcordeRepository()


@lru_cache
def bloque_service() -> BloqueService:
    return BloqueService(_repo_bloques())


@lru_cache
def leccion_service() -> LeccionService:
    return LeccionService(_repo_lecciones())


@lru_cache
def ejercicio_service() -> EjercicioService:
    return EjercicioService(_repo_ejercicios())


@lru_cache
def acorde_service() -> AcordeService:
    return AcordeService(_repo_acordes())


@lru_cache
def progreso_service() -> ProgresoService:
    # Lecciones y ejercicios por SQL (tablas con FK). Los bloques siguen en la tabla
    # `progreso` via Supabase REST con el token del estudiante hasta HU-B-308.
    return ProgresoService(
        session_scope,
        SqlProgresoRepository(),
        progreso_bloques=SupabaseProgresoRepository(),
        lecciones=SqlLeccionRepository(session_scope),
        ejercicios=SqlEjercicioRepository(session_scope),
    )


@lru_cache
def quiz_service() -> QuizService:
    # Preguntas por SQL (HU-B-313): la anon key ya no puede leer respuesta_correcta.
    # El resultado del bloque sigue en `progreso` via Supabase REST hasta HU-B-308.
    return QuizService(SqlQuizRepository(session_scope), SupabaseProgresoRepository())


@lru_cache
def perfil_service() -> PerfilService:
    # Perfiles y roles siempre por SQL: el rol no depende de RLS ni del token.
    return PerfilService(session_scope, SqlPerfilRepository())


@lru_cache
def admin_usuarios_service() -> AdminUsuariosService:
    return AdminUsuariosService(session_scope, SqlPerfilRepository())


def rol_de_usuario(usuario_id: str) -> str | None:
    return perfil_service().rol_de(usuario_id)
