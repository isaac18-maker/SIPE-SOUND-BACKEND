# =========================================================
# Registra el CRUD de un tipo de contenido sobre un blueprint (HU-B-309).
# Lecciones, ejercicios (panel docente) y bloques (admin) comparten la
# misma forma de endpoints; cada uno aporta sus esquemas y su servicio.
# =========================================================
from collections.abc import Callable

from flask import Blueprint, request
from pydantic import BaseModel

from app.core.responses import created, ok, paginated
from app.core.security import get_current_user, roles_required
from app.schemas.contenido import EstadoIn, FiltrosContenido
from app.services.contenido_service import ContenidoService


def registrar_crud(  # noqa: PLR0913 - configuracion declarativa de un recurso
    bp: Blueprint,
    *,
    recurso: str,
    nombre: str,
    servicio: Callable[[], ContenidoService],
    crear: type[BaseModel],
    editar: type[BaseModel],
    roles: tuple[str, ...],
) -> None:
    """recurso: segmento de la URL (p. ej. "docente/lecciones"); nombre: "lección"."""
    base = f"/{recurso}"
    clave = recurso.replace("/", "_")
    proteger = roles_required(*roles)

    def listar():
        filtros = FiltrosContenido.model_validate(request.args.to_dict())
        filas, total = servicio().listar(
            get_current_user(),
            filtros.model_dump(exclude={"pagina", "por_pagina"}),
            pagina=filtros.pagina,
            por_pagina=filtros.por_pagina,
        )
        return paginated(filas, pagina=filtros.pagina, por_pagina=filtros.por_pagina, total=total)

    def crear_uno():
        datos = crear.model_validate(request.get_json(silent=True) or {})
        fila = servicio().crear(get_current_user(), datos.model_dump())
        return created(fila, mensaje=f"Se creó {nombre} como borrador.")

    def obtener(ident: int):
        return ok(servicio().obtener(get_current_user(), ident))

    def editar_uno(ident: int):
        datos = editar.model_validate(request.get_json(silent=True) or {})
        fila = servicio().actualizar(get_current_user(), ident, datos.cambios())
        return ok(fila, mensaje="Cambios guardados.")

    def cambiar_estado(ident: int):
        entrada = EstadoIn.model_validate(request.get_json(silent=True) or {})
        fila = servicio().cambiar_estado(get_current_user(), ident, entrada.estado)
        return ok(fila, mensaje=f"Estado: {fila['estado']}.")

    def eliminar(ident: int):
        servicio().eliminar(get_current_user(), ident)
        return ok(None, mensaje=f"Se eliminó {nombre}.")

    listar.__doc__ = f"Listar ({nombre}): ?estado=&q=&pagina=&por_pagina= y filtros por relacion."
    crear_uno.__doc__ = f"Crear {nombre} (queda en borrador)."
    obtener.__doc__ = f"Detalle de {nombre}."
    editar_uno.__doc__ = f"Editar {nombre}: solo los campos enviados."
    cambiar_estado.__doc__ = "Cambiar estado: borrador -> publicado -> archivado -> borrador."
    eliminar.__doc__ = f"Eliminar {nombre}. Si esta en uso responde 409: archivala en su lugar."

    rutas = (
        (base, "listar", listar, ["GET"]),
        (base, "crear", crear_uno, ["POST"]),
        (f"{base}/<int:ident>", "obtener", obtener, ["GET"]),
        (f"{base}/<int:ident>", "editar", editar_uno, ["PATCH"]),
        (f"{base}/<int:ident>/estado", "estado", cambiar_estado, ["PATCH"]),
        (f"{base}/<int:ident>", "eliminar", eliminar, ["DELETE"]),
    )
    for regla, accion, vista, metodos in rutas:
        bp.add_url_rule(regla, f"{clave}_{accion}", proteger(vista), methods=metodos)
