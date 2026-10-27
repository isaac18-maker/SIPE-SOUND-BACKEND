from flask import Blueprint, request

from app.container import progreso_docente_service
from app.core.constants import ROL_ADMIN, ROL_DOCENTE
from app.core.responses import ok
from app.core.security import get_current_user, roles_required
from app.schemas.progreso_docente import (
    DetalleProgresoQuery,
    MatrizQuery,
    ProgresoQuery,
    SeriesQuery,
)

bp = Blueprint("docente_progreso", __name__)

PANEL = (ROL_DOCENTE, ROL_ADMIN)


def _texto(valor) -> str | None:
    return str(valor) if valor is not None else None


@bp.get("/docente/progreso")
@roles_required(*PANEL)
def resumen_de_progreso():
    """Cifras por curso (avance promedio, al dia, sin actividad), el desempeno por bloque y la
    lista de estudiantes que necesitan apoyo. Sin ?curso_id= abarca todos tus cursos activos."""
    filtros = ProgresoQuery.model_validate(request.args.to_dict())
    return ok(
        progreso_docente_service().resumen(
            get_current_user(), filtros.curso_id, _texto(filtros.docente_id)
        )
    )


@bp.get("/docente/progreso/series")
@roles_required(*PANEL)
def series_de_progreso():
    """Datos para las graficas: actividad por dia, distribucion del avance en cinco tramos,
    estados (sin_iniciar/en_curso/finalizado) y desempeno de cada evaluacion. Filtros:
    ?curso_id=&bloque_id=&dias=7-90&estudiantes=al_dia|sin_actividad|en_riesgo."""
    filtros = SeriesQuery.model_validate(request.args.to_dict())
    datos = filtros.model_dump()
    datos["docente_id"] = _texto(filtros.docente_id)
    return ok(progreso_docente_service().series(get_current_user(), datos))


@bp.get("/docente/progreso/matriz")
@roles_required(*PANEL)
def matriz_de_progreso():
    """Estudiantes x bloques de la ruta de un curso, con el estado y el mejor puntaje de cada
    celda. ?curso_id= obligatorio; ?q=&orden=nombre|-avance_pct|-ultimo_avance&pagina=&por_pagina=.
    El encabezado de bloques va en meta.bloques."""
    filtros = MatrizQuery.model_validate(request.args.to_dict())
    consulta = filtros.model_dump(exclude={"curso_id"})
    filas, total, bloques = progreso_docente_service().matriz(
        get_current_user(), filtros.curso_id, consulta
    )
    meta = {
        "pagina": filtros.pagina,
        "por_pagina": filtros.por_pagina,
        "total": total,
        "bloques": bloques,
    }
    return ok(filas, meta=meta)


@bp.get("/docente/progreso/estudiantes/<uuid:estudiante_id>")
@roles_required(*PANEL)
def progreso_de_un_estudiante(estudiante_id):
    """Progreso de un estudiante en todos tus cursos donde esta inscrito."""
    filtros = DetalleProgresoQuery.model_validate(request.args.to_dict())
    return ok(
        progreso_docente_service().estudiante(
            get_current_user(), str(estudiante_id), _texto(filtros.docente_id)
        )
    )
