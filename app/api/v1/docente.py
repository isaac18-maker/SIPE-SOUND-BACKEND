from flask import Blueprint, request

from app.api.v1._crud_contenido import registrar_crud
from app.container import curso_service, ejercicio_contenido_service, leccion_contenido_service
from app.core.constants import ROL_ADMIN, ROL_DOCENTE
from app.core.responses import created, ok, paginated
from app.core.security import get_current_user, roles_required
from app.schemas.contenido import EjercicioCrear, EjercicioEditar, LeccionCrear, LeccionEditar
from app.schemas.curso import (
    CursoCreate,
    CursoEditar,
    CursosQuery,
    EstudiantesQuery,
    RetroalimentacionIn,
    RutaCursoIn,
)

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


# --- Cursos, estudiantes y retroalimentacion (HU-B-310) ---------------------
@bp.get("/docente/resumen")
@roles_required(*PANEL)
def resumen():
    """Cifras del panel, estudiantes sin actividad en 14 dias y actividad reciente."""
    return ok(curso_service().resumen(get_current_user()))


@bp.get("/docente/cursos")
@roles_required(*PANEL)
def listar_cursos():
    """Cursos propios (admin: todos). ?estado=activo|archivado."""
    filtros = CursosQuery.model_validate(request.args.to_dict())
    archivados = filtros.estado == "archivado"
    return ok(curso_service().listar_de_docente(get_current_user(), archivados=archivados))


@bp.post("/docente/cursos")
@roles_required(*PANEL)
def crear_curso():
    """Crear un curso: se genera su codigo de invitacion."""
    datos = CursoCreate.model_validate(request.get_json(silent=True) or {})
    curso = curso_service().crear(get_current_user(), datos)
    return created(curso, mensaje=f"Curso creado. Código: {curso['codigo_invitacion']}.")


@bp.get("/docente/cursos/<int:curso_id>")
@roles_required(*PANEL)
def detalle_curso(curso_id: int):
    """Detalle del curso con su ruta y el numero de estudiantes."""
    return ok(curso_service().detalle(get_current_user(), curso_id))


@bp.patch("/docente/cursos/<int:curso_id>")
@roles_required(*PANEL)
def editar_curso(curso_id: int):
    datos = CursoEditar.model_validate(request.get_json(silent=True) or {})
    curso = curso_service().actualizar(get_current_user(), curso_id, datos.cambios())
    return ok(curso, mensaje="Cambios guardados.")


@bp.delete("/docente/cursos/<int:curso_id>")
@roles_required(*PANEL)
def archivar_curso(curso_id: int):
    """Archivar (no se borra: el historial de los estudiantes se conserva)."""
    return ok(curso_service().archivar(get_current_user(), curso_id), mensaje="Curso archivado.")


@bp.post("/docente/cursos/<int:curso_id>/codigo")
@roles_required(*PANEL)
def regenerar_codigo(curso_id: int):
    """Nuevo codigo de invitacion; el anterior deja de servir."""
    curso = curso_service().regenerar_codigo(get_current_user(), curso_id)
    return ok(curso, mensaje=f"Nuevo código: {curso['codigo_invitacion']}.")


@bp.put("/docente/cursos/<int:curso_id>/bloques")
@roles_required(*PANEL)
def definir_ruta(curso_id: int):
    """Ruta del curso: [{bloque_id, orden}] (reemplaza la anterior)."""
    ruta = RutaCursoIn.model_validate(request.get_json(silent=True) or {})
    return ok(curso_service().definir_ruta(get_current_user(), curso_id, ruta))


@bp.get("/docente/cursos/<int:curso_id>/estudiantes")
@roles_required(*PANEL)
def estudiantes(curso_id: int):
    """Estudiantes con avance. ?q=&orden=nombre|-avance_pct|-ultimo_avance&pagina=&por_pagina=."""
    filtros = EstudiantesQuery.model_validate(request.args.to_dict())
    filas, total = curso_service().estudiantes(get_current_user(), curso_id, filtros.model_dump())
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.get("/docente/cursos/<int:curso_id>/estudiantes/<uuid:estudiante_id>")
@roles_required(*PANEL)
def detalle_estudiante(curso_id: int, estudiante_id):
    """Progreso por bloque, intentos y comentarios del estudiante en este curso."""
    detalle = curso_service().detalle_estudiante(get_current_user(), curso_id, str(estudiante_id))
    return ok(detalle)


@bp.delete("/docente/cursos/<int:curso_id>/estudiantes/<uuid:estudiante_id>")
@roles_required(*PANEL)
def retirar_estudiante(curso_id: int, estudiante_id):
    """Retirar del curso: borra la inscripcion, no el progreso del estudiante."""
    curso_service().retirar(get_current_user(), curso_id, str(estudiante_id))
    return ok(None, mensaje="Estudiante retirado del curso. Su progreso se conserva.")


@bp.post("/docente/cursos/<int:curso_id>/estudiantes/<uuid:estudiante_id>/retroalimentaciones")
@roles_required(*PANEL)
def comentar(curso_id: int, estudiante_id):
    """Enviar un comentario (1-1000 caracteres) al estudiante."""
    entrada = RetroalimentacionIn.model_validate(request.get_json(silent=True) or {})
    fila = curso_service().comentar(
        get_current_user(), curso_id, str(estudiante_id), entrada.mensaje
    )
    return created(fila, mensaje="Comentario enviado.")
