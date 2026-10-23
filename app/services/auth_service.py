# =========================================================
# Autenticacion a traves del backend (HU-B-322). El frontend ya no
# conoce Supabase: registra, inicia, renueva y cierra sesion aqui.
#   - access token: viaja en el cuerpo y el frontend lo guarda en memoria.
#   - refresh token: solo en una cookie httpOnly (la pone la ruta, no el servicio).
# El rol nunca sale del token: lo sigue leyendo /me desde profiles (HU-B-304).
# =========================================================
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import NoAutenticado, ServicioNoDisponible
from app.schemas.auth import InicioSesionIn, RegistroIn

MENSAJE_SIN_SESION = "Necesitas iniciar sesión."


class ProveedorIdentidad(Protocol):
    def registrar(self, *, email: str, password: str, nombre: str) -> dict[str, Any]: ...
    def iniciar_sesion(self, *, email: str, password: str) -> dict[str, Any]: ...
    def refrescar(self, refresh_token: str) -> dict[str, Any]: ...
    def cerrar_sesion(self, access_token: str) -> None: ...


@dataclass(frozen=True)
class SesionEmitida:
    """Lo que devuelve la API (`publica`) y lo que va a la cookie (`refresh_token`)."""

    publica: dict[str, Any]
    refresh_token: str


class AuthService:
    def __init__(self, proveedor: ProveedorIdentidad) -> None:
        self._proveedor = proveedor

    def registrar(self, datos: RegistroIn) -> dict[str, Any]:
        """La respuesta es la misma exista o no el correo: no revela que cuentas existen."""
        self._proveedor.registrar(email=datos.email, password=datos.password, nombre=datos.nombre)
        return {"email": datos.email, "requiere_confirmacion": True}

    def iniciar_sesion(self, datos: InicioSesionIn) -> SesionEmitida:
        return _sesion(self._proveedor.iniciar_sesion(email=datos.email, password=datos.password))

    def refrescar(self, refresh_token: str | None) -> SesionEmitida:
        if not refresh_token:
            raise NoAutenticado(MENSAJE_SIN_SESION)
        return _sesion(self._proveedor.refrescar(refresh_token))

    def cerrar_sesion(self, access_token: str | None) -> None:
        """Sin token o con uno vencido solo se borra la cookie (la ruta siempre lo hace)."""
        if not access_token:
            return
        try:
            self._proveedor.cerrar_sesion(access_token)
        except NoAutenticado:
            return


def _sesion(respuesta: dict[str, Any]) -> SesionEmitida:
    usuario = respuesta.get("user") or {}
    access_token = respuesta.get("access_token")
    refresh_token = respuesta.get("refresh_token")
    if not access_token or not refresh_token or not usuario.get("id"):
        raise ServicioNoDisponible("El servicio de cuentas respondió sin sesión.")
    metadatos = usuario.get("user_metadata") or {}
    return SesionEmitida(
        publica={
            "access_token": access_token,
            "token_type": "bearer",
            "expira_en": respuesta.get("expires_at"),
            "usuario": {
                "id": usuario["id"],
                "email": usuario.get("email"),
                "nombre": metadatos.get("nombre"),
            },
        },
        refresh_token=refresh_token,
    )
