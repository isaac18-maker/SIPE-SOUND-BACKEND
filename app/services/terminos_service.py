# =========================================================
# Terminos y condiciones (HU-B-411): un texto vigente en Markdown con numero de version. Una
# version nueva obliga a todas las cuentas a leerla y aceptarla antes de seguir usando la API
# (la aceptacion de cada cuenta vive en profiles.terminos_version).
# =========================================================
import logging
from typing import Any, Protocol

from app.core.errors import Conflicto
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

logger = logging.getLogger(__name__)

MENSAJE_VERSION_DESACTUALIZADA = (
    "Los términos cambiaron mientras los leías. Recarga la página para ver la versión vigente."
)


class RepositorioTerminos(Protocol):
    def vigente(self, sesion: Any) -> Fila: ...
    def version_vigente(self, sesion: Any) -> int: ...
    def reemplazar(
        self, sesion: Any, contenido: str, *, nueva_version: bool, admin_id: str
    ) -> None: ...
    def aceptar(self, sesion: Any, usuario_id: str, version: int) -> None: ...


class TerminosService:
    def __init__(self, abrir_sesion: AbrirSesion, terminos: RepositorioTerminos) -> None:
        self._abrir_sesion = abrir_sesion
        self._terminos = terminos

    def vigente(self) -> Fila:
        """Publico: lo lee el visitante en /terminos y quien debe aceptarlos."""
        with self._abrir_sesion() as sesion:
            return self._terminos.vigente(sesion)

    def version_vigente(self) -> int:
        with self._abrir_sesion() as sesion:
            return self._terminos.version_vigente(sesion)

    def actualizar(self, admin: CurrentUser, contenido: str, *, nueva_version: bool) -> Fila:
        with self._abrir_sesion() as sesion:
            self._terminos.reemplazar(
                sesion, contenido, nueva_version=nueva_version, admin_id=admin.id
            )
            vigente = self._terminos.vigente(sesion)
        logger.info(
            "Terminos actualizados: admin=%s version=%s nueva_version=%s",
            admin.id,
            vigente["version"],
            nueva_version,
        )
        return vigente

    def aceptar(self, usuario: CurrentUser, version: int) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            vigente = self._terminos.version_vigente(sesion)
            if version != vigente:
                raise Conflicto(MENSAJE_VERSION_DESACTUALIZADA)
            self._terminos.aceptar(sesion, usuario.id, vigente)
        return {"version": vigente}


def terminos_pendientes(perfil: dict[str, Any] | None, version_vigente: int) -> bool:
    """Sin perfil no hay nada que exigir; con perfil, falta aceptar si su version es menor."""
    if perfil is None:
        return False
    return (perfil.get("terminos_version") or 0) < version_vigente
