from flask import Blueprint, request

from app.container import actividad_docente_service, admin_cursos_service
from app.core.constants import ROL_ADMIN
from app.core.responses import created, ok, paginated
from app.core.security import get_current_user, roles_required
from app.schemas.admin_cursos import (
    CursoAdminCrear,
    FiltrosActividadDocentes,
    FiltrosCursosAdmin,
    FiltrosDocentes,
    LineaDeTiempoQuery,
    ReasignarCursoIn,
    ResumenActividadQuery,
)
from app.schemas.curso import EstudiantesQuery

bp = Blueprint("admin_cursos", __name__)

SUGERENCIA_CODIGO = "Si compartió el código del curso, pídele al docente que lo regenere."


@bp.get("/admin/docentes")
@roles_required(ROL_ADMIN)
def listar_docentes():
    """Docentes con su estado, sus cursos (activos y archivados) y sus estudiantes. ?q=&pagina=."""
    filtros = FiltrosDocentes.model_validate(request.args.to_dict())
    filas, total = admin_cursos_service().listar_docentes(filtros.model_dump())
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.get("/admin/docentes/actividad")
@roles_required(ROL_ADMIN)
def actividad_de_docentes():
    """Un renglon por docente activo con su estado de actividad (activo: algo en los ultimos 7
    dias; inactivo: entre 8 y 30; sin_actividad: mas de 30 o nunca). ?estado_actividad=&q=
    &orden=ultima_actividad|-acciones_30d|nombre&pagina=. Sin datos de estudiantes."""
    filtros = FiltrosActividadDocentes.model_validate(request.args.to_dict())
    filas, total = actividad_docente_service().listar(filtros.model_dump())
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.get("/admin/docentes/<uuid:docente_id>/actividad/resumen")
@roles_required(ROL_ADMIN)
def resumen_de_actividad(docente_id):
    """Actividad por dia (con los dias vacios), por tipo y sus cursos asignados con el avance de
    sus estudiantes. ?dias= de 7 a 90 (28 por defecto). 404 si no es un docente."""
    consulta = ResumenActividadQuery.model_validate(request.args.to_dict())
    return ok(actividad_docente_service().resumen(str(docente_id), consulta.dias))


@bp.get("/admin/docentes/<uuid:docente_id>/actividad")
@roles_required(ROL_ADMIN)
def linea_de_tiempo_del_docente(docente_id):
    """Linea de tiempo, la mas reciente primero. ?tipo=&curso_id=&desde=&hasta=&pagina=."""
    filtros = LineaDeTiempoQuery.model_validate(request.args.to_dict())
    filas, total = actividad_docente_service().linea_de_tiempo(
        str(docente_id), filtros.model_dump()
    )
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.get("/admin/docentes/<uuid:docente_id>/cursos")
@roles_required(ROL_ADMIN)
def cursos_de_docente(docente_id):
    """Cursos de un docente (activos y archivados). 404 si la cuenta no es de un docente."""
    return ok(admin_cursos_service().cursos_de_docente(str(docente_id)))


@bp.get("/admin/cursos")
@roles_required(ROL_ADMIN)
def listar_cursos():
    """Todos los cursos. ?docente_id=&estado=activo|archivado&q=&pagina=&por_pagina=."""
    filtros = FiltrosCursosAdmin.model_validate(request.args.to_dict())
    consulta = filtros.model_dump()
    if filtros.docente_id is not None:
        consulta["docente_id"] = str(filtros.docente_id)
    filas, total = admin_cursos_service().listar_cursos(consulta)
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.post("/admin/cursos")
@roles_required(ROL_ADMIN)
def crear_curso():
    """Crea un curso. Sin `docente_id` queda disponible hasta que el admin le asigne uno; con
    `docente_id`, ese docente recibe el correo de asignacion."""
    datos = CursoAdminCrear.model_validate(request.get_json(silent=True) or {})
    cuerpo = datos.model_dump()
    cuerpo["docente_id"] = str(datos.docente_id) if datos.docente_id else None
    return created(
        admin_cursos_service().crear(get_current_user().id, cuerpo), mensaje="Curso creado."
    )


@bp.patch("/admin/cursos/<int:curso_id>/docente")
@roles_required(ROL_ADMIN)
def asignar_docente(curso_id: int):
    """Asigna el curso a un docente con la cuenta activa: si no tenia docente lo asigna; si tenia,
    lo reasigna (sus estudiantes y evaluaciones se mantienen). El docente de destino recibe un
    correo. Permite cursos archivados: la FK de cursos impide eliminar a un docente que aun los
    tiene."""
    datos = ReasignarCursoIn.model_validate(request.get_json(silent=True) or {})
    curso = admin_cursos_service().asignar(get_current_user().id, curso_id, str(datos.docente_id))
    return ok(curso, mensaje="Curso asignado.")


@bp.delete("/admin/cursos/<int:curso_id>/docente")
@roles_required(ROL_ADMIN)
def quitar_docente(curso_id: int):
    """El curso queda disponible: sus estudiantes, ruta y evaluaciones se conservan. 409 si ya
    no tenia docente."""
    curso = admin_cursos_service().quitar_docente(get_current_user().id, curso_id)
    return ok(curso, mensaje="El curso quedó sin docente y disponible.")


@bp.get("/admin/cursos/<int:curso_id>/estudiantes")
@roles_required(ROL_ADMIN)
def estudiantes_del_curso(curso_id: int):
    """Estudiantes del curso con avance, igual que el panel del docente pero con el correo
    completo. ?q=&orden=nombre|-avance_pct|-ultimo_avance&pagina=&por_pagina=."""
    filtros = EstudiantesQuery.model_validate(request.args.to_dict())
    filas, total = admin_cursos_service().estudiantes_de_curso(curso_id, filtros.model_dump())
    return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)


@bp.delete("/admin/cursos/<int:curso_id>/estudiantes/<uuid:estudiante_id>")
@roles_required(ROL_ADMIN)
def revocar_inscripcion(curso_id: int, estudiante_id):
    """Revoca el acceso del estudiante a este curso. Borra la inscripcion, no su progreso."""
    admin_cursos_service().revocar_inscripcion(get_current_user().id, curso_id, str(estudiante_id))
    return ok(None, mensaje=f"Acceso revocado. Su progreso se conserva. {SUGERENCIA_CODIGO}")


@bp.delete("/admin/usuarios/<uuid:usuario_id>/cursos")
@roles_required(ROL_ADMIN)
def revocar_todas_las_inscripciones(usuario_id):
    """Retira a la persona de todos sus cursos activos (p. ej. cambio de colegio)."""
    revocadas = admin_cursos_service().revocar_todas(get_current_user().id, str(usuario_id))
    return ok(
        {"revocadas": revocadas},
        mensaje=f"Retiramos a la persona de {revocadas} curso(s). {SUGERENCIA_CODIGO}",
    )
