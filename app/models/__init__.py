"""Importar este paquete registra todos los modelos en Base.metadata (lo usa Alembic)."""

from app.models.acorde import Acorde
from app.models.base import Base, auth_users
from app.models.bloque import Bloque
from app.models.curso import Curso
from app.models.curso_bloque import CursoBloque
from app.models.docente_preautorizado import DocentePreautorizado
from app.models.ejercicio import Ejercicio
from app.models.evaluacion import Evaluacion, IntentoEvaluacion, PreguntaEvaluacion
from app.models.inscripcion import Inscripcion
from app.models.leccion import Leccion
from app.models.profile import Profile
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.models.retroalimentacion import Retroalimentacion

__all__ = [
    "Acorde",
    "Base",
    "Bloque",
    "Curso",
    "CursoBloque",
    "DocentePreautorizado",
    "Ejercicio",
    "Evaluacion",
    "IntentoEvaluacion",
    "Inscripcion",
    "Leccion",
    "PreguntaEvaluacion",
    "Profile",
    "ProgresoEjercicio",
    "ProgresoLeccion",
    "Retroalimentacion",
    "auth_users",
]
