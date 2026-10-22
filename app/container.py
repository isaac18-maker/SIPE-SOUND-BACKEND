# =========================================================
# Composition root: el UNICO lugar que decide que implementacion
# de repositorio recibe cada servicio (inversion de dependencias).
# Vive fuera de core/ porque depende de services y repositories.
# =========================================================
from functools import lru_cache

from app.repositories.supabase.acorde_repository import SupabaseAcordeRepository
from app.repositories.supabase.bloque_repository import SupabaseBloqueRepository
from app.repositories.supabase.ejercicio_repository import SupabaseEjercicioRepository
from app.repositories.supabase.leccion_repository import SupabaseLeccionRepository
from app.repositories.supabase.progreso_repository import SupabaseProgresoRepository
from app.repositories.supabase.quiz_repository import SupabaseQuizRepository
from app.services.acorde_service import AcordeService
from app.services.bloque_service import BloqueService
from app.services.ejercicio_service import EjercicioService
from app.services.leccion_service import LeccionService
from app.services.progreso_service import ProgresoService
from app.services.quiz_service import QuizService


@lru_cache
def bloque_service() -> BloqueService:
    return BloqueService(SupabaseBloqueRepository())


@lru_cache
def leccion_service() -> LeccionService:
    return LeccionService(SupabaseLeccionRepository())


@lru_cache
def ejercicio_service() -> EjercicioService:
    return EjercicioService(SupabaseEjercicioRepository())


@lru_cache
def acorde_service() -> AcordeService:
    return AcordeService(SupabaseAcordeRepository())


@lru_cache
def progreso_service() -> ProgresoService:
    return ProgresoService(
        SupabaseProgresoRepository(),
        lecciones=SupabaseLeccionRepository(),
        ejercicios=SupabaseEjercicioRepository(),
    )


@lru_cache
def quiz_service() -> QuizService:
    return QuizService(SupabaseQuizRepository(), SupabaseProgresoRepository())
