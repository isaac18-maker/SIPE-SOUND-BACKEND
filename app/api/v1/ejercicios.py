from flask import Blueprint, request

from app.container import ejercicio_service
from app.core.responses import ok
from app.core.security import usuario_opcional
from app.schemas.ejercicio import EjerciciosQuery

bp = Blueprint("ejercicios", __name__)


@bp.get("/ejercicios")
def listar_ejercicios():
    """Catalogo publico. Con sesion cada ejercicio trae `mi_progreso` (HU-B-501):
    estado sin_iniciar|en_curso|finalizado, mejor_bpm y ultimo_registro. ?estado= (solo con
    sesion) y ?leccion_id= filtran."""
    filtros = EjerciciosQuery.model_validate(request.args.to_dict())
    usuario = usuario_opcional()
    return ok(
        ejercicio_service().listar(
            estudiante_id=usuario.id if usuario else None,
            estado=filtros.estado,
            leccion_id=filtros.leccion_id,
        )
    )
