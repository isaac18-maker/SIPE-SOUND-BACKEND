# =========================================================
# Mi cuenta: cambiar contrasena y correo SIN permiso del administrador, pero confirmando la
# identidad (HU-B-404). Cada cambio exige dos pruebas:
#   1. la contrasena actual (se comprueba con Supabase y la sesion que crea se revoca), y
#   2. un codigo de 6 digitos enviado al correo ACTUAL (10 min, un solo uso).
# Con ambas se emite un token_reautenticacion: 5 minutos, un solo uso, atado a la persona y a
# la sesion del JWT, que autoriza UN cambio. El cambio de correo ademas confirma un codigo
# enviado al correo nuevo. Nunca se registran contrasenas, codigos ni tokens.
# =========================================================
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.constants import (
    CORREO_CAMBIAR_CORREO,
    CORREO_CONTRASENA_CAMBIADA,
    CORREO_CORREO_CAMBIADO,
    CORREO_REAUTENTICACION,
    PROPOSITO_CAMBIAR_CORREO,
    PROPOSITO_REAUTENTICADO,
    PROPOSITO_REAUTENTICAR,
    VIGENCIA_CODIGO_MIN,
)
from app.core.errors import AppError, Conflicto, NoAutenticado, NoEncontrado, ReglaNegocio
from app.core.privacidad import enmascarar_email
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, RepositorioCuentas
from app.services.auth_service import ProveedorIdentidad
from app.services.codigo_service import CodigoService
from app.services.recuperacion_service import fecha_para_correo
from app.services.verificacion_service import MENSAJE_CODIGO_INVALIDO, EnviadorDeCorreo

MENSAJE_CONTRASENA_ACTUAL = "La contraseña actual no coincide."
MENSAJE_REAUTENTICAR = "Vuelve a confirmar tu identidad."
MENSAJE_CONTRASENA_IGUAL = "La contraseña nueva debe ser distinta de la actual."
MENSAJE_CORREO_IGUAL = "Ese ya es el correo de tu cuenta."
MENSAJE_CORREO_EN_USO = "Ese correo ya está en uso."
MENSAJE_SESION = "Inicia sesión de nuevo."


class CuentaService:
    def __init__(  # noqa: PLR0913 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        cuentas: RepositorioCuentas,
        codigos: CodigoService,
        correo: EnviadorDeCorreo,
        proveedor: ProveedorIdentidad,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._cuentas = cuentas
        self._codigos = codigos
        self._correo = correo
        self._proveedor = proveedor

    # --- Verificacion de identidad -------------------------------------------------------
    def pedir_codigo_de_identidad(
        self, usuario: CurrentUser, password_actual: str
    ) -> dict[str, Any]:
        cuenta = self._cuenta(usuario)
        self._exigir_password_actual(cuenta["email"], password_actual)
        with self._abrir_sesion() as sesion:
            codigo = self._codigos.emitir(
                sesion, usuario.id, PROPOSITO_REAUTENTICAR, cuenta["email"]
            )
        self._correo.enviar(
            CORREO_REAUTENTICACION,
            cuenta["email"],
            {
                "nombre": cuenta["nombre"],
                "codigo": codigo,
                "minutos": VIGENCIA_CODIGO_MIN[PROPOSITO_REAUTENTICAR],
            },
            usuario_id=usuario.id,
        )
        return {"enviado_a": enmascarar_email(cuenta["email"])}

    def confirmar_identidad(self, usuario: CurrentUser, codigo: str) -> dict[str, Any]:
        sesion_id = self._sesion_de(usuario)
        with self._abrir_sesion() as sesion:
            valido = self._codigos.consumir(sesion, usuario.id, PROPOSITO_REAUTENTICAR, codigo)
            token = (
                self._codigos.emitir_token(
                    sesion, usuario.id, PROPOSITO_REAUTENTICADO, ambito=sesion_id
                )
                if valido
                else None
            )
        # Fuera del with: un codigo errado debe confirmar el intento fallido, no deshacerlo.
        if token is None:
            raise ReglaNegocio(MENSAJE_CODIGO_INVALIDO)
        vigencia = timedelta(minutes=VIGENCIA_CODIGO_MIN[PROPOSITO_REAUTENTICADO])
        return {
            "token_reautenticacion": token,
            "expira_en": (datetime.now(UTC) + vigencia).isoformat(timespec="seconds"),
        }

    # --- Contrasena -----------------------------------------------------------------------
    def cambiar_contrasena(self, usuario: CurrentUser, token: str, password_nueva: str) -> None:
        sesion_id = self._sesion_de(usuario)
        cuenta = self._cuenta(usuario)
        # Antes de gastar el token: si la contrasena nueva ya es la actual, no hay cambio.
        self._exigir_distinta(cuenta["email"], password_nueva)
        with self._abrir_sesion() as sesion:
            self._consumir_identidad(sesion, usuario, token, sesion_id)
            self._cuentas.fijar_contrasena(sesion, usuario.id, password_nueva)
            # Las demas sesiones se cierran; esta sigue abierta.
            self._cuentas.cerrar_sesiones(sesion, usuario.id, excepto=sesion_id)
        self._correo.enviar(
            CORREO_CONTRASENA_CAMBIADA,
            cuenta["email"],
            {"nombre": cuenta["nombre"], "fecha": fecha_para_correo(datetime.now(UTC))},
            usuario_id=usuario.id,
        )

    # --- Correo ---------------------------------------------------------------------------
    def pedir_cambio_de_correo(self, usuario: CurrentUser, token: str, email_nuevo: str) -> None:
        sesion_id = self._sesion_de(usuario)
        cuenta = self._cuenta(usuario)
        if email_nuevo == cuenta["email"].lower():
            raise ReglaNegocio(MENSAJE_CORREO_IGUAL)
        with self._abrir_sesion() as sesion:
            # Si el correo esta en uso, se lanza dentro del with: la transaccion se deshace y
            # el token NO se gasta (la persona puede probar con otro correo).
            if self._cuentas.correo_en_uso(sesion, email_nuevo, excepto_id=usuario.id):
                raise Conflicto(MENSAJE_CORREO_EN_USO)
            self._consumir_identidad(sesion, usuario, token, sesion_id)
            codigo = self._codigos.emitir(sesion, usuario.id, PROPOSITO_CAMBIAR_CORREO, email_nuevo)
        # El codigo va al correo NUEVO: asi se prueba que la persona lo controla.
        self._correo.enviar(
            CORREO_CAMBIAR_CORREO,
            email_nuevo,
            {
                "nombre": cuenta["nombre"],
                "codigo": codigo,
                "minutos": VIGENCIA_CODIGO_MIN[PROPOSITO_CAMBIAR_CORREO],
            },
            usuario_id=usuario.id,
        )

    def confirmar_cambio_de_correo(self, usuario: CurrentUser, codigo: str) -> dict[str, Any]:
        sesion_id = self._sesion_de(usuario)
        cuenta = self._cuenta(usuario)
        nuevo: str | None = None
        with self._abrir_sesion() as sesion:
            fila = self._codigos.consumir_completo(
                sesion, usuario.id, PROPOSITO_CAMBIAR_CORREO, codigo
            )
            if fila is not None:
                nuevo = fila["email_destino"]
                if self._cuentas.correo_en_uso(sesion, nuevo, excepto_id=usuario.id):
                    raise Conflicto(MENSAJE_CORREO_EN_USO)
                self._cuentas.cambiar_correo(sesion, usuario.id, nuevo)
                self._cuentas.cerrar_sesiones(sesion, usuario.id, excepto=sesion_id)
        if nuevo is None:
            raise ReglaNegocio(MENSAJE_CODIGO_INVALIDO)
        # Al correo ANTERIOR: si no fue la persona, es la unica forma de enterarse a tiempo.
        self._correo.enviar(
            CORREO_CORREO_CAMBIADO,
            cuenta["email"],
            {
                "nombre": cuenta["nombre"],
                "correo_nuevo": enmascarar_email(nuevo),
                "fecha": fecha_para_correo(datetime.now(UTC)),
            },
            usuario_id=usuario.id,
        )
        return {"email": nuevo}

    # --- Auxiliares -----------------------------------------------------------------------
    def _cuenta(self, usuario: CurrentUser) -> dict[str, Any]:
        """Correo y nombre desde la base: el correo del JWT queda viejo tras un cambio."""
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.datos_de_aviso(sesion, usuario.id)
        if cuenta is None:
            raise NoEncontrado("No encontramos tu cuenta.")
        return cuenta

    @staticmethod
    def _sesion_de(usuario: CurrentUser) -> str:
        # El token de identidad se ata a la sesion: robarlo desde otra sesion no sirve.
        if not usuario.session_id:
            raise NoAutenticado(MENSAJE_SESION)
        return usuario.session_id

    def _consumir_identidad(
        self, sesion: Any, usuario: CurrentUser, token: str, sesion_id: str
    ) -> None:
        duenio = self._codigos.consumir_token(
            sesion, PROPOSITO_REAUTENTICADO, token, ambito=sesion_id
        )
        if duenio != usuario.id:
            raise ReglaNegocio(MENSAJE_REAUTENTICAR)

    def _exigir_password_actual(self, email: str, password: str) -> None:
        try:
            sesion = self._proveedor.iniciar_sesion(email=email, password=password)
        except NoAutenticado:
            raise NoAutenticado(MENSAJE_CONTRASENA_ACTUAL) from None
        self._revocar(sesion)

    def _exigir_distinta(self, email: str, password_nueva: str) -> None:
        try:
            sesion = self._proveedor.iniciar_sesion(email=email, password=password_nueva)
        except NoAutenticado:
            return  # no coincide con la actual: es distinta
        self._revocar(sesion)
        raise ReglaNegocio(MENSAJE_CONTRASENA_IGUAL)

    def _revocar(self, respuesta: dict[str, Any]) -> None:
        """La comprobacion abre una sesion en Supabase; se cierra de inmediato (solo esa)."""
        token = respuesta.get("access_token")
        if token:
            with suppress(AppError):
                self._proveedor.cerrar_sesion(token)
