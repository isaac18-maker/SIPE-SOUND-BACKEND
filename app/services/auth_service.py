# =========================================================
# Autenticacion a traves del backend (HU-B-322). El frontend ya no
# conoce Supabase: registra, inicia, renueva y cierra sesion aqui.
#   - access token: viaja en el cuerpo y el frontend lo guarda en memoria.
#   - refresh token: solo en una cookie httpOnly (la pone la ruta, no el servicio).
# El rol nunca sale del token: lo sigue leyendo /me desde profiles (HU-B-304).
# =========================================================
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.constants import (
    CUENTA_PENDIENTE,
    CUENTA_SUSPENDIDA,
    MENSAJE_SIN_CONFIRMAR,
    MENSAJE_SUSPENDIDA,
)
from app.core.errors import (
    AppError,
    Conflicto,
    CuentaExistente,
    NoAutenticado,
    ReglaNegocio,
    ServicioNoDisponible,
    SinPermiso,
)
from app.schemas.auth import InicioSesionIn, RegistroIn

MENSAJE_SIN_SESION = "Necesitas iniciar sesión."
MENSAJE_SESION_VENCIDA = "Tu sesión terminó. Inicia sesión de nuevo."
MENSAJE_CORREO_REGISTRADO = (
    "Este correo ya tiene una cuenta. Inicia sesión o, si no recuerdas tu contraseña, recupérala."
)


class EmisorDeCodigos(Protocol):
    """Lo cumple VerificacionService."""

    def enviar_codigo(self, email: str) -> int: ...
    def estado_de_registro(self, email: str) -> dict[str, Any] | None: ...


class ProveedorIdentidad(Protocol):
    def registrar(
        self, *, email: str, password: str, nombre: str, apellido: str | None = None
    ) -> dict[str, Any]: ...
    def iniciar_sesion(self, *, email: str, password: str) -> dict[str, Any]: ...
    def refrescar(self, refresh_token: str) -> dict[str, Any]: ...
    def cerrar_sesion(self, access_token: str) -> None: ...


@dataclass(frozen=True)
class SesionEmitida:
    """Lo que devuelve la API (`publica`) y lo que va a la cookie (`refresh_token`)."""

    publica: dict[str, Any]
    refresh_token: str


class AuthService:
    def __init__(
        self,
        proveedor: ProveedorIdentidad,
        verificacion: EmisorDeCodigos,
        estado_de: Callable[[str], str | None],
    ) -> None:
        self._proveedor = proveedor
        self._verificacion = verificacion
        self._estado_de = estado_de

    def registrar(self, datos: RegistroIn) -> dict[str, Any]:
        """Crea la cuenta y envia el codigo (HU-B-402, lo envia el backend, no Supabase).

        Si el correo ya tiene una cuenta verificada responde 409. Si tiene un registro en
        curso no vuelve a crearla: devuelve `registro_en_curso` y los segundos que le quedan
        al codigo, para que la persona escriba el que tiene o pida otro (HU-B-416).
        """
        previo = self._verificacion.estado_de_registro(datos.email)
        if previo and previo["estado"] == "verificada":
            raise Conflicto(MENSAJE_CORREO_REGISTRADO, meta={"correo_registrado": True})
        if previo:
            return {
                "email": datos.email,
                "requiere_confirmacion": True,
                "registro_en_curso": True,
                "vence_en_segundos": previo["vence_en_segundos"],
            }
        try:
            respuesta = self._proveedor.registrar(
                email=datos.email,
                password=datos.password,
                nombre=datos.nombre,
                apellido=datos.apellido,
            )
        except CuentaExistente:
            respuesta = {}
        # Con "Confirm email" desactivado Supabase devuelve una sesion al registrar: no se
        # entrega ni se deja viva (la cuenta aun no esta verificada).
        if token := respuesta.get("access_token"):
            self._revocar(token)
        vence = self._verificacion.enviar_codigo(datos.email)
        return {
            "email": datos.email,
            "requiere_confirmacion": True,
            "registro_en_curso": False,
            "vence_en_segundos": vence,
        }

    def iniciar_sesion(self, datos: InicioSesionIn) -> SesionEmitida:
        sesion = _sesion(self._proveedor.iniciar_sesion(email=datos.email, password=datos.password))
        estado = self._estado_de(sesion.publica["usuario"]["id"])
        if estado == CUENTA_SUSPENDIDA:
            self._revocar(sesion.publica["access_token"])
            raise SinPermiso(MENSAJE_SUSPENDIDA)
        if estado == CUENTA_PENDIENTE:
            self._revocar(sesion.publica["access_token"])
            raise ReglaNegocio(MENSAJE_SIN_CONFIRMAR, meta={"requiere_verificacion": True})
        return sesion

    def refrescar(self, refresh_token: str | None) -> SesionEmitida:
        if not refresh_token:
            raise NoAutenticado(MENSAJE_SIN_SESION)
        sesion = _sesion(self._proveedor.refrescar(refresh_token))
        if self._estado_de(sesion.publica["usuario"]["id"]) in {
            CUENTA_PENDIENTE,
            CUENTA_SUSPENDIDA,
        }:
            self._revocar(sesion.publica["access_token"])
            raise NoAutenticado(MENSAJE_SESION_VENCIDA)
        return sesion

    def _revocar(self, access_token: str) -> None:
        with suppress(AppError):
            self._proveedor.cerrar_sesion(access_token)

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
