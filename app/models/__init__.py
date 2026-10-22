"""Importar este paquete registra todos los modelos en Base.metadata (lo usa Alembic)."""

from app.models.acorde import Acorde
from app.models.base import Base, auth_users
from app.models.bloque import Bloque
from app.models.ejercicio import Ejercicio
from app.models.leccion import Leccion
from app.models.partitura import Partitura
from app.models.profile import Profile
from app.models.progreso import Progreso
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.models.quiz_pregunta import QuizPregunta

__all__ = [
    "Acorde",
    "Base",
    "Bloque",
    "Ejercicio",
    "Leccion",
    "Partitura",
    "Profile",
    "Progreso",
    "ProgresoEjercicio",
    "ProgresoLeccion",
    "QuizPregunta",
    "auth_users",
]
