from flask import Blueprint, request

from app.api.v1._crud_contenido import registrar_crud
from app.container import (
    acorde_service,
    admin_cuentas_service,
    admin_usuarios_service,
    bloque_contenido_service,
    docente_service,
    solicitud_nombre_service,
)
from app.core.constants import PROPOSITO_VERIFICAR_CORREO, ROL_ADMIN, VIGENCIA_CODIGO_MIN
from app.core.errors import NoEncontrado
from app.core.responses import created, ok
from app.core.security import get_current_user, roles_required
from app.schemas.admin_cuentas import (
    AccionEnLoteIn,
    CambioEstadoIn,
    EditarCuentaIn,
    EliminarCuentaIn,
    FiltrosUsuarios,
    VerificacionManualIn,
)
from app.schemas.contenido import BloqueCrear, BloqueEditar
from app.schemas.docente import PreautorizacionDocenteIn
from app.schemas.mensajes import ResolverSolicitudNombreIn, SolicitudesNombreQuery
from app.schemas.perfil import CambioRolIn, PermisoNombreEnLoteIn, PermisoNombreIn
from app.schemas.video import VideoAcordeIn

bp = Blueprint("admin", __name__)

# Catalogo global de bloques de la ruta (contrato 4.4).
registrar_crud(
    bp,
    recurso="admin/bloques",
    nombre="el bloque",
    servicio=bloque_contenido_service,
    crear=BloqueCrear,
    editar=BloqueEditar,
    roles=(ROL_ADMIN,),
)


@bp.put("/admin/acordes/<int:acorde_id>/video")
@roles_required(ROL_ADMIN)
def asignar_video_de_acorde(acorde_id: int):
    """Video guia de un acorde (catalogo global: solo el administrador). Guarda el id de
    YouTube; no se guarda ni se devuelve la URL."""
    datos = VideoAcordeIn.model_validate(request.get_json(silent=True) or {})
    acorde = acorde_service().asignar_video(acorde_id, datos.video_url, datos.video_inicio_seg)
    return ok(acorde, mensaje="Video guardado.")


@bp.delete("/admin/acordes/<int:acorde_id>/video")
@roles_required(ROL_ADMIN)
def quitar_video_de_acorde(acorde_id: int):
    """Quita el video guia del acorde."""
    return ok(acorde_service().quitar_video(acorde_id), mensaje="Video quitado.")


@bp.patch("/admin/usuarios/<uuid:usuario_id>/rol")
@roles_required(ROL_ADMIN)
def cambiar_rol(usuario_id):
    """Cambia el rol (el propio no). `notificar` avisa por correo a la persona."""
    entrada = CambioRolIn.model_validate(request.get_json(silent=True) or {})
    cuenta = admin_usuarios_service().cambiar_rol(
        get_current_user().id, str(usuario_id), entrada.rol
    )
    if entrada.notificar:
        admin_cuentas_service().avisar_cambio_de_rol(str(usuario_id), entrada.rol)
    return ok(cuenta)


@bp.get("/admin/usuarios")
@roles_required(ROL_ADMIN)
def listar_usuarios():
    """Todas las cuentas con su estado (pendiente_verificacion, activa, suspendida), el ultimo
    envio del codigo y sus cursos. Filtros: ?rol=&estado=&q=&puede_editar_nombre=&orden=. En
    meta.totales va el numero de cuentas por estado y en meta.roles por rol (sin depender de
    los filtros)."""
    filtros = FiltrosUsuarios.model_validate(request.args.to_dict())
    filas, total, totales, roles = admin_cuentas_service().listar(filtros.model_dump())
    meta = {
        "pagina": filtros.pagina,
        "por_pagina": filtros.por_pagina,
        "total": total,
        "totales": totales,
        "roles": roles,
    }
    return ok(filas, meta=meta)


@bp.post("/admin/usuarios/lote")
@roles_required(ROL_ADMIN)
def accion_en_lote():
    """Cambia el rol, activa, suspende o reenvia el codigo a hasta 100 cuentas. Procesa solo las
    validas: omite la propia cuenta y las que ya estan en ese estado (data.omitidas)."""
    datos = AccionEnLoteIn.model_validate(request.get_json(silent=True) or {})
    resultado = admin_cuentas_service().en_lote(
        get_current_user().id,
        [str(i) for i in datos.ids],
        datos.accion,
        rol=datos.rol,
        notificar=datos.notificar,
    )
    return ok(resultado)


@bp.get("/admin/usuarios/<uuid:usuario_id>")
@roles_required(ROL_ADMIN)
def detalle_usuario(usuario_id):
    """Detalle: inscripciones, cursos a cargo, resumen de progreso y ultimas acciones del admin."""
    return ok(admin_cuentas_service().detalle(str(usuario_id)))


@bp.patch("/admin/usuarios/<uuid:usuario_id>")
@roles_required(ROL_ADMIN)
def editar_usuario(usuario_id):
    """Nombre, apellido y correo (los tres obligatorios). Un correo nuevo deja la cuenta
    pendiente y envia un codigo; el administrador no cambia asi su propio correo."""
    datos = EditarCuentaIn.model_validate(request.get_json(silent=True) or {})
    cuenta = admin_cuentas_service().editar(
        get_current_user().id, str(usuario_id), datos.nombre, datos.apellido, datos.email
    )
    return ok(cuenta, mensaje="Cambios guardados.")


@bp.post("/admin/usuarios/<uuid:usuario_id>/verificacion/reenviar")
@roles_required(ROL_ADMIN)
def reenviar_verificacion(usuario_id):
    """Envia un codigo nuevo a una cuenta con el correo sin verificar (el anterior deja de
    servir). El resultado del envio se ve en ultimo_envio_verificacion del detalle."""
    correo = admin_cuentas_service().reenviar_verificacion(get_current_user().id, str(usuario_id))
    minutos = VIGENCIA_CODIGO_MIN[PROPOSITO_VERIFICAR_CORREO]
    vigencia = f"{minutos} {'minuto' if minutos == 1 else 'minutos'}"
    return ok(None, mensaje=f"Enviamos el código a {correo}. Vence en {vigencia}.")


@bp.post("/admin/usuarios/<uuid:usuario_id>/verificacion")
@roles_required(ROL_ADMIN)
def verificar_manualmente(usuario_id):
    """Verifica el correo sin el codigo (aulas donde la persona no puede abrir su correo)."""
    datos = VerificacionManualIn.model_validate(request.get_json(silent=True) or {})
    admin_cuentas_service().verificar_manual(get_current_user().id, str(usuario_id), datos.motivo)
    return ok(None, mensaje="Correo verificado a mano. Queda registrado con tu motivo.")


@bp.patch("/admin/usuarios/<uuid:usuario_id>/estado")
@roles_required(ROL_ADMIN)
def cambiar_estado(usuario_id):
    """Suspende (cierra sus sesiones; `notificar` avisa por correo) o reactiva una cuenta."""
    datos = CambioEstadoIn.model_validate(request.get_json(silent=True) or {})
    resultado = admin_cuentas_service().cambiar_estado(
        get_current_user().id,
        str(usuario_id),
        datos.estado,
        datos.motivo,
        notificar=datos.notificar,
    )
    return ok(resultado)


@bp.delete("/admin/usuarios/<uuid:usuario_id>")
@roles_required(ROL_ADMIN)
def eliminar_usuario(usuario_id):
    """Borra la cuenta y sus datos. No se puede deshacer: el cuerpo lleva el correo de la
    cuenta como confirmacion. 409 si es un docente con cursos a cargo."""
    datos = EliminarCuentaIn.model_validate(request.get_json(silent=True) or {})
    admin_cuentas_service().eliminar(get_current_user().id, str(usuario_id), datos.confirmacion)
    return ok(None, mensaje="Cuenta eliminada.")


@bp.patch("/admin/usuarios/<uuid:usuario_id>/permisos")
@roles_required(ROL_ADMIN)
def permiso_de_nombre(usuario_id):
    """Permite o impide que una persona cambie su nombre y apellido."""
    datos = PermisoNombreIn.model_validate(request.get_json(silent=True) or {})
    actualizados, _ = admin_usuarios_service().permiso_de_nombre(
        get_current_user().id, [str(usuario_id)], datos.puede_editar_nombre
    )
    if not actualizados:
        raise NoEncontrado(f"No existe el usuario {usuario_id}")
    return ok({"id": str(usuario_id), "puede_editar_nombre": datos.puede_editar_nombre})


@bp.post("/admin/usuarios/permisos")
@roles_required(ROL_ADMIN)
def permiso_de_nombre_en_lote():
    """Igual que el anterior para hasta 100 personas a la vez. Los ids que no existen se
    ignoran y se informan en meta.no_encontrados."""
    datos = PermisoNombreEnLoteIn.model_validate(request.get_json(silent=True) or {})
    ids = [str(i) for i in datos.usuario_ids]
    actualizados, faltan = admin_usuarios_service().permiso_de_nombre(
        get_current_user().id, ids, datos.puede_editar_nombre
    )
    return ok({"actualizados": len(actualizados)}, meta={"no_encontrados": faltan})


@bp.get("/admin/solicitudes-nombre")
@roles_required(ROL_ADMIN)
def solicitudes_de_nombre():
    """Solicitudes de cambio de nombre de estudiantes y docentes (HU-B-415): quien la envio
    (nombre y rol, sin correo), su texto y su estado. ?estado=&rol=estudiante|docente.
    meta.totales: pendientes, aceptadas y rechazadas de cada rol."""
    filtros = SolicitudesNombreQuery.model_validate(request.args.to_dict())
    filas, totales = solicitud_nombre_service().listar(filtros.estado, filtros.rol)
    return ok(filas, meta={"totales": totales})


@bp.patch("/admin/solicitudes-nombre/<uuid:solicitud_id>")
@roles_required(ROL_ADMIN)
def resolver_solicitud_de_nombre(solicitud_id):
    """Aceptar habilita el cambio de nombre de esa cuenta (queda en la auditoria); rechazar la
    cierra sin cambios. 409 si ya se resolvio."""
    datos = ResolverSolicitudNombreIn.model_validate(request.get_json(silent=True) or {})
    resuelta = solicitud_nombre_service().resolver(
        get_current_user(), str(solicitud_id), datos.estado
    )
    habilitado = datos.estado == "aceptada"
    mensaje = "Habilitaste el cambio de nombre." if habilitado else "Rechazaste la solicitud."
    return ok(resuelta, mensaje=mensaje)


@bp.post("/admin/docentes/preautorizaciones")
@roles_required(ROL_ADMIN)
def preautorizar_docente():
    """Autorizar un correo como docente.

    La persona se registra normalmente y recibe el rol 'docente' al confirmar su correo.
    Si ya tiene una cuenta confirmada, el rol se asigna de inmediato (estado "aplicada").
    """
    datos = PreautorizacionDocenteIn.model_validate(request.get_json(silent=True) or {})
    fila = docente_service().preautorizar(datos.email, get_current_user().id)
    if fila["estado"] == "aplicada":
        return created(fila, mensaje=f"{datos.email} ya tenía cuenta: ahora es docente.")
    return created(fila, mensaje=f"Listo: {datos.email} será docente cuando confirme su correo.")


@bp.get("/admin/docentes/preautorizaciones")
@roles_required(ROL_ADMIN)
def listar_preautorizaciones():
    """Correos autorizados como docente, con su estado (pendiente / aplicada)."""
    return ok(docente_service().listar())


@bp.delete("/admin/docentes/preautorizaciones/<path:email>")
@roles_required(ROL_ADMIN)
def revocar_preautorizacion(email: str):
    """Retirar una preautorizacion que aun no se usa."""
    datos = PreautorizacionDocenteIn.model_validate({"email": email})
    docente_service().revocar(datos.email)
    return ok(None, mensaje="Preautorización retirada.")
