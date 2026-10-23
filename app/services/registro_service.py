# =========================================================
# Alta de cuentas por rol (HU-B-318):
#   estudiante -> registro publico (correo de confirmacion)
#   docente    -> invitacion de un administrador
#   admin      -> nunca por la API: scripts.promover_admin o PATCH de otro admin
# =========================================================
from typing import Any, Protocol

from app.core.constants import ROL_DOCENTE
from app.core.errors import ServicioNoDisponible
from app.repositories.base import AbrirSesion, RepositorioPerfiles
from app.schemas.registro import InvitacionDocenteIn, RegistroIn


class ProveedorCuentas(Protocol):
    def registrar(self, *, email: str, password: str, nombre: str) -> dict[str, Any]: ...
    def invitar(self, *, email: str, nombre: str) -> dict[str, Any]: ...


class RegistroService:
    def __init__(
        self,
        cuentas: ProveedorCuentas,
        abrir_sesion: AbrirSesion,
        perfiles: RepositorioPerfiles,
    ) -> None:
        self._cuentas = cuentas
        self._abrir_sesion = abrir_sesion
        self._perfiles = perfiles

    def registrar_estudiante(self, datos: RegistroIn) -> dict[str, Any]:
        """La respuesta es la misma exista o no el correo: no revela que cuentas existen.
        El perfil (rol 'estudiante') lo crea el trigger de la base."""
        self._cuentas.registrar(email=datos.email, password=datos.password, nombre=datos.nombre)
        return {"email": datos.email, "requiere_confirmacion": True}

    def invitar_docente(self, datos: InvitacionDocenteIn) -> dict[str, Any]:
        """Crea la cuenta por invitacion y la deja con rol 'docente' desde el inicio."""
        usuario = self._cuentas.invitar(email=datos.email, nombre=datos.nombre)
        with self._abrir_sesion() as sesion:
            if self._perfiles.obtener_para_actualizar(sesion, usuario["id"]) is None:
                # El trigger on_auth_user_created no creo el perfil: estado inesperado.
                raise ServicioNoDisponible(
                    "La cuenta se creó, pero no su perfil. Revisa el trigger."
                )
            perfil = self._perfiles.actualizar_rol(sesion, usuario["id"], ROL_DOCENTE)
        return {
            "id": perfil["id"],
            "email": datos.email,
            "nombre": perfil["nombre"],
            "rol": perfil["rol"],
            "invitacion_enviada": True,
        }
