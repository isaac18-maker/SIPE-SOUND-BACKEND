"""Importar este paquete registra todos los modelos en Base.metadata (lo usa Alembic)."""

from app.models.accion_admin import AccionAdmin
from app.models.acorde import Acorde
from app.models.base import Base, auth_users
from app.models.bloque import Bloque
from app.models.codigo_verificacion import CodigoVerificacion
from app.models.curso import Curso
from app.models.curso_bloque import CursoBloque
from app.models.docente_preautorizado import DocentePreautorizado
from app.models.documento_legal import DocumentoLegal
from app.models.ejercicio import Ejercicio
from app.models.envio_correo import EnvioCorreo
from app.models.evaluacion import Evaluacion, IntentoEvaluacion, PreguntaEvaluacion
from app.models.inscripcion import Inscripcion
from app.models.leccion import Leccion
from app.models.mensaje import Mensaje, MensajeDestinatario
from app.models.profile import Profile
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.models.retroalimentacion import Retroalimentacion
from app.models.solicitud_inscripcion import SolicitudInscripcion

__all__ = [
    "AccionAdmin",
    "Acorde",
    "Base",
    "Bloque",
    "CodigoVerificacion",
    "Curso",
    "CursoBloque",
    "DocentePreautorizado",
    "DocumentoLegal",
    "Ejercicio",
    "EnvioCorreo",
    "Evaluacion",
    "IntentoEvaluacion",
    "Inscripcion",
    "Leccion",
    "Mensaje",
    "MensajeDestinatario",
    "PreguntaEvaluacion",
    "Profile",
    "ProgresoEjercicio",
    "ProgresoLeccion",
    "Retroalimentacion",
    "SolicitudInscripcion",
    "auth_users",
]
