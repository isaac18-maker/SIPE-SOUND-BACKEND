from flask import Blueprint, request

from app.api.v1._crud_contenido import registrar_crud
from app.container import admin_usuarios_service, bloque_contenido_service, docente_service
from app.core.constants import ROL_ADMIN
from app.core.errors import NoEncontrado
from app.core.responses import created, ok
from app.core.security import get_current_user, roles_required
from app.schemas.contenido import BloqueCrear, BloqueEditar
from app.schemas.docente import PreautorizacionDocenteIn
from app.schemas.perfil import CambioRolIn, PermisoNombreEnLoteIn, PermisoNombreIn

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


@bp.patch("/admin/usuarios/<uuid:usuario_id>/rol")
@roles_required(ROL_ADMIN)
def cambiar_rol(usuario_id):
    entrada = CambioRolIn.model_validate(request.get_json(silent=True) or {})
    return ok(admin_usuarios_service().cambiar_rol(str(usuario_id), entrada.rol))


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
