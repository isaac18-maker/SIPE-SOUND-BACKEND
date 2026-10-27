from flask import Blueprint, request

from app.container import mensajeria_service
from app.core.constants import ROL_ADMIN, ROL_DOCENTE, ROL_ESTUDIANTE
from app.core.responses import created, ok
from app.core.security import get_current_user, roles_required
from app.schemas.mensajes import (
    BuscarDestinatariosQuery,
    FiltrosBandeja,
    HiloEditarIn,
    MensajeCrearIn,
)

bp = Blueprint("mensajes", __name__)

# Cualquier persona con sesion y rol: roles_required carga el rol desde la base (nunca del token).
TODOS = (ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN)


@bp.post("/mensajes")
@roles_required(*TODOS)
def enviar_mensaje():
    """Mensaje nuevo (alcance + asunto + cuerpo) o respuesta (respuesta_a_id + cuerpo).
    Las reglas de destino y los limites por hora estan en el servicio."""
    datos = MensajeCrearIn.model_validate(request.get_json(silent=True) or {})
    resultado = mensajeria_service().enviar(get_current_user(), datos.datos())
    return created(resultado, mensaje="Mensaje enviado.")


@bp.get("/mensajes")
@roles_required(*TODOS)
def bandeja():
    """Bandeja de hilos (el ultimo mensaje de cada uno). ?filtro=recibidos|enviados|no_leidos|
    archivados&q=asunto&pagina=&por_pagina=."""
    filtros = FiltrosBandeja.model_validate(request.args.to_dict())
    filas, total = mensajeria_service().bandeja(get_current_user(), filtros.model_dump())
    meta = {"pagina": filtros.pagina, "por_pagina": filtros.por_pagina, "total": total}
    return ok(filas, meta=meta)


@bp.get("/mensajes/no-leidos")
@roles_required(*TODOS)
def no_leidos():
    """Contador de mensajes sin leer (el frontend lo consulta cada 60 s)."""
    return ok(mensajeria_service().no_leidos(get_current_user()))


@bp.get("/mensajes/destinatarios")
@roles_required(*TODOS)
def destinatarios():
    """Personas, cursos y grupos a los que esta persona puede escribir (max. 20). Un estudiante
    solo ve a los docentes de sus cursos. ?q= (2 a 80 caracteres) busca por nombre."""
    filtros = BuscarDestinatariosQuery.model_validate(request.args.to_dict())
    return ok(mensajeria_service().destinatarios(get_current_user(), filtros.q))


@bp.get("/mensajes/hilos/<uuid:hilo_id>")
@roles_required(*TODOS)
def ver_hilo(hilo_id):
    """Los mensajes del hilo que enviaste o recibiste. Los marca como leidos."""
    return ok(mensajeria_service().hilo(get_current_user(), str(hilo_id)))


@bp.patch("/mensajes/hilos/<uuid:hilo_id>")
@roles_required(*TODOS)
def editar_hilo(hilo_id):
    """{archivado: bool} archiva o recupera el hilo; {leido: false} lo deja sin leer."""
    datos = HiloEditarIn.model_validate(request.get_json(silent=True) or {})
    resultado = mensajeria_service().editar_hilo(
        get_current_user(), str(hilo_id), archivado=datos.archivado, leido=datos.leido
    )
    return ok(resultado)
