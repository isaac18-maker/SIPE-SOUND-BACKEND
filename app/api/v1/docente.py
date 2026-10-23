from flask import Blueprint

from app.api.v1._crud_contenido import registrar_crud
from app.container import ejercicio_contenido_service, leccion_contenido_service
from app.core.constants import ROL_ADMIN, ROL_DOCENTE
from app.schemas.contenido import EjercicioCrear, EjercicioEditar, LeccionCrear, LeccionEditar

bp = Blueprint("docente", __name__)

PANEL = (ROL_DOCENTE, ROL_ADMIN)

registrar_crud(
    bp,
    recurso="docente/lecciones",
    nombre="la lección",
    servicio=leccion_contenido_service,
    crear=LeccionCrear,
    editar=LeccionEditar,
    roles=PANEL,
)
registrar_crud(
    bp,
    recurso="docente/ejercicios",
    nombre="el ejercicio",
    servicio=ejercicio_contenido_service,
    crear=EjercicioCrear,
    editar=EjercicioEditar,
    roles=PANEL,
)
