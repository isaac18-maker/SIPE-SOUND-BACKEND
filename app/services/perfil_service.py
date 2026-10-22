from typing import Any

from app.core.constants import ROL_ADMIN
from app.core.errors import Conflicto, NoEncontrado
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, RepositorioPerfiles

CAMPOS_PERFIL = ("id", "nombre", "rol", "nivel")


class PerfilService:
    def __init__(self, abrir_sesion: AbrirSesion, perfiles: RepositorioPerfiles) -> None:
        self._abrir_sesion = abrir_sesion
        self._perfiles = perfiles

    def mi_perfil(self, usuario: CurrentUser) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener(sesion, usuario.id)
        if perfil is None:
            raise NoEncontrado("No encontramos tu perfil.")
        return {**{campo: perfil[campo] for campo in CAMPOS_PERFIL}, "email": usuario.email}

    def rol_de(self, usuario_id: str) -> str | None:
        """El rol sale de la base, nunca del token: el usuario puede editar su user_metadata."""
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener(sesion, usuario_id)
        return perfil["rol"] if perfil else None


class AdminUsuariosService:
    def __init__(self, abrir_sesion: AbrirSesion, perfiles: RepositorioPerfiles) -> None:
        self._abrir_sesion = abrir_sesion
        self._perfiles = perfiles

    def cambiar_rol(self, usuario_id: str, rol: str) -> dict[str, Any]:
        """Asigna un rol. Nunca deja el sistema sin al menos un administrador."""
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener_para_actualizar(sesion, usuario_id)
            if perfil is None:
                raise NoEncontrado(f"No existe el usuario {usuario_id}")
            deja_de_ser_admin = perfil["rol"] == ROL_ADMIN and rol != ROL_ADMIN
            if deja_de_ser_admin and self._perfiles.contar_por_rol(sesion, ROL_ADMIN) <= 1:
                raise Conflicto(
                    "No se puede quitar el rol al único administrador. "
                    "Asigna primero otro administrador."
                )
            actualizado = self._perfiles.actualizar_rol(sesion, usuario_id, rol)
        return {campo: actualizado[campo] for campo in CAMPOS_PERFIL}
