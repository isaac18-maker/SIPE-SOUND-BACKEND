import logging
from typing import Any

from app.core.constants import (
    CUENTA_ACTIVA,
    CUENTA_PENDIENTE,
    CUENTA_SUSPENDIDA,
    ROL_ADMIN,
    ROL_DOCENTE,
    ROL_ESTUDIANTE,
)
from app.core.errors import Conflicto, NoEncontrado, SinPermiso
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, RepositorioAcciones, RepositorioPerfiles

logger = logging.getLogger(__name__)

CAMPOS_PERFIL = ("id", "nombre", "apellido", "rol", "nivel", "puede_editar_nombre")
MENSAJE_NOMBRE_BLOQUEADO = "El administrador no ha habilitado el cambio de nombre en tu cuenta."


def estado_de_cuenta(perfil: dict[str, Any] | None) -> str | None:
    """Estado calculado de una cuenta (00-decisiones-fase-4, seccion 3). None = sin perfil."""
    if perfil is None:
        return None
    if perfil["suspendido_en"]:
        return CUENTA_SUSPENDIDA  # gana sobre "pendiente": primero se resuelve la suspension
    return CUENTA_ACTIVA if perfil["correo_verificado_en"] else CUENTA_PENDIENTE


class PerfilService:
    def __init__(self, abrir_sesion: AbrirSesion, perfiles: RepositorioPerfiles) -> None:
        self._abrir_sesion = abrir_sesion
        self._perfiles = perfiles

    def mi_perfil(self, usuario: CurrentUser) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener(sesion, usuario.id)
            email = self._perfiles.email_de(sesion, usuario.id)
        if perfil is None:
            raise NoEncontrado("No encontramos tu perfil.")
        return {
            **{campo: perfil[campo] for campo in CAMPOS_PERFIL},
            "email": email or usuario.email,
            "correo_verificado_en": perfil["correo_verificado_en"],
            "terminos_version": perfil["terminos_version"],
        }

    def editar_nombre(self, usuario: CurrentUser, cambios: dict[str, str]) -> dict[str, Any]:
        """Nombre y apellido: solo con el permiso que da un administrador (que siempre puede)."""
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener_para_actualizar(sesion, usuario.id)
            if perfil is None:
                raise NoEncontrado("No encontramos tu perfil.")
            if not perfil["puede_editar_nombre"] and perfil["rol"] != ROL_ADMIN:
                raise SinPermiso(MENSAJE_NOMBRE_BLOQUEADO)
            self._perfiles.actualizar_nombre(sesion, usuario.id, cambios)
        # Sin los valores: son datos personales.
        logger.info("Nombre actualizado: usuario=%s campos=%s", usuario.id, sorted(cambios))
        return self.mi_perfil(usuario)

    def perfil_de(self, usuario_id: str) -> dict[str, Any] | None:
        with self._abrir_sesion() as sesion:
            return self._perfiles.obtener(sesion, usuario_id)

    def rol_de(self, usuario_id: str) -> str | None:
        """El rol sale de la base, nunca del token: el usuario puede editar su user_metadata."""
        with self._abrir_sesion() as sesion:
            perfil = self._perfiles.obtener(sesion, usuario_id)
        return perfil["rol"] if perfil else None


class AdminUsuariosService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        perfiles: RepositorioPerfiles,
        auditoria: RepositorioAcciones,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._perfiles = perfiles
        self._auditoria = auditoria

    def _exigir_sin_cursos_a_cargo(
        self, sesion: Any, usuario_id: str, rol_actual: str, rol_nuevo: str
    ) -> None:
        """Un docente con cursos activos no pasa a estudiante: sus cursos quedarian a cargo de
        alguien que ya no puede gestionarlos (HU-B-406). Primero se reasignan."""
        if rol_actual != ROL_DOCENTE or rol_nuevo != ROL_ESTUDIANTE:
            return
        a_cargo = self._perfiles.contar_cursos_activos_a_cargo(sesion, usuario_id)
        if a_cargo:
            raise Conflicto(
                f"Reasigna sus cursos activos ({a_cargo}) antes de quitarle el rol de docente."
            )

    def permiso_de_nombre(
        self, admin_id: str, usuario_ids: list[str], permitido: bool
    ) -> tuple[list[str], list[str]]:
        """Activa o quita el permiso para editar el nombre. Devuelve (actualizados,
        no_encontrados): los ids que no existen se ignoran."""
        with self._abrir_sesion() as sesion:
            actualizados = self._perfiles.actualizar_permiso_nombre(sesion, usuario_ids, permitido)
            for usuario_id in actualizados:
                self._auditoria.registrar(
                    sesion,
                    admin_id=admin_id,
                    usuario_id=usuario_id,
                    accion="permiso_nombre",
                    detalle={"permitido": permitido},
                )
        encontrados = set(actualizados)
        faltan = [i for i in usuario_ids if i not in encontrados]
        logger.info(
            "Permiso de nombre: admin=%s permitido=%s actualizados=%d",
            admin_id,
            permitido,
            len(actualizados),
        )
        return actualizados, faltan

    def cambiar_rol(self, admin_id: str, usuario_id: str, rol: str) -> dict[str, Any]:
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
            self._exigir_sin_cursos_a_cargo(sesion, usuario_id, perfil["rol"], rol)
            actualizado = self._perfiles.actualizar_rol(sesion, usuario_id, rol)
            self._auditoria.registrar(
                sesion,
                admin_id=admin_id,
                usuario_id=usuario_id,
                accion="cambiar_rol",
                detalle={"de": perfil["rol"], "a": rol},
            )
        return {campo: actualizado[campo] for campo in CAMPOS_PERFIL}
