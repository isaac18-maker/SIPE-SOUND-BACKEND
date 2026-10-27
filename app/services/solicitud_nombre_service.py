# =========================================================
# Solicitudes de cambio de nombre (HU-B-415). Ademas del aviso a los administradores (mensajeria,
# HU-B-407), la solicitud queda como una fila PENDIENTE que un administrador acepta (activa el
# permiso de editar el nombre de esa cuenta) o rechaza. Una pendiente por persona. Sin correos.
# =========================================================
import logging
from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy.exc import IntegrityError

from app.core.constants import ROL_ADMIN
from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

logger = logging.getLogger(__name__)

MENSAJE_ADMIN_SIN_SOLICITUD = "Los administradores pueden cambiar su nombre sin pedir permiso."
MENSAJE_YA_PENDIENTE = "Ya tienes una solicitud pendiente: espera la respuesta de un administrador."
MENSAJE_YA_RESUELTA = "Esa solicitud ya fue resuelta."


class RepositorioSolicitudesNombre(Protocol):
    def hay_pendiente(self, sesion: Any, usuario_id: str) -> bool: ...
    def crear(self, sesion: Any, usuario_id: str, mensaje: str) -> Fila: ...
    def ultima_de(self, sesion: Any, usuario_id: str) -> Fila | None: ...
    def listar(self, sesion: Any, estado: str | None, rol: str | None) -> list[Fila]: ...
    def totales(self, sesion: Any) -> dict[str, dict[str, int]]: ...
    def obtener_para_resolver(self, sesion: Any, solicitud_id: str) -> Fila | None: ...
    def resolver(self, sesion: Any, solicitud_id: str, estado: str, por: str) -> Fila | None: ...


# (admin_id, usuario_ids, permitido) -> (actualizados, no_encontrados): AdminUsuariosService.
ConcederPermiso = Callable[[str, list[str], bool], tuple[list[str], list[str]]]
# (usuario, texto) -> resultado: el aviso a los administradores de MensajeriaService.
AvisarAdmins = Callable[[CurrentUser, str], dict[str, Any]]


class SolicitudNombreService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        solicitudes: RepositorioSolicitudesNombre,
        conceder_permiso: ConcederPermiso,
        avisar_admins: AvisarAdmins,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._solicitudes = solicitudes
        self._conceder_permiso = conceder_permiso
        self._avisar_admins = avisar_admins

    # --- Estudiante y docente ------------------------------------------------------
    def solicitar(self, usuario: CurrentUser, mensaje: str) -> dict[str, Any]:
        if usuario.rol == ROL_ADMIN:
            raise ReglaNegocio(MENSAJE_ADMIN_SIN_SOLICITUD)
        with self._abrir_sesion() as sesion:
            if self._solicitudes.hay_pendiente(sesion, usuario.id):
                raise Conflicto(MENSAJE_YA_PENDIENTE)
        aviso = self._avisar_admins(usuario, mensaje)
        with self._abrir_sesion() as sesion:
            try:
                with sesion.begin_nested():  # savepoint: la unica pendiente puede colisionar
                    solicitud = self._solicitudes.crear(sesion, usuario.id, mensaje)
            except IntegrityError as error:
                raise Conflicto(MENSAJE_YA_PENDIENTE) from error
        return {**solicitud, "destinatarios": aviso["destinatarios"]}

    def la_mia(self, usuario: CurrentUser) -> Fila | None:
        """La ultima solicitud de la persona (para mostrar "pendiente" en su cuenta)."""
        with self._abrir_sesion() as sesion:
            return self._solicitudes.ultima_de(sesion, usuario.id)

    # --- Administrador ----------------------------------------------------------------
    def listar(
        self, estado: str | None, rol: str | None
    ) -> tuple[list[Fila], dict[str, dict[str, int]]]:
        with self._abrir_sesion() as sesion:
            return self._solicitudes.listar(sesion, estado, rol), self._solicitudes.totales(sesion)

    def resolver(self, admin: CurrentUser, solicitud_id: str, estado: str) -> Fila:
        """Aceptar activa el permiso de editar el nombre de esa cuenta; rechazar solo la cierra."""
        with self._abrir_sesion() as sesion:
            solicitud = self._solicitudes.obtener_para_resolver(sesion, solicitud_id)
            if solicitud is None:
                raise NoEncontrado("No existe esa solicitud.")
            if solicitud["estado"] != "pendiente":
                raise Conflicto(MENSAJE_YA_RESUELTA)
            # Primero el permiso: si falla, la solicitud sigue pendiente (se revierte todo).
            if estado == "aceptada":
                self._conceder_permiso(admin.id, [solicitud["usuario_id"]], True)
            resuelta = self._solicitudes.resolver(sesion, solicitud_id, estado, admin.id)
            if resuelta is None:
                raise Conflicto(MENSAJE_YA_RESUELTA)
        logger.info("Solicitud de nombre %s: admin=%s estado=%s", solicitud_id, admin.id, estado)
        return resuelta
