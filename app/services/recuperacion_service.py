# =========================================================
# Restablecer la contrasena con un enlace de un solo uso (HU-B-403).
#   1. pedir_enlace: si el correo tiene una cuenta verificada, envia un enlace con un token
#      (32 bytes, solo se guarda su HMAC, vence en 15 min, un solo uso).
#   2. restablecer: en UNA transaccion consume el token, fija la contrasena y cierra todas
#      las sesiones; despues avisa por correo del cambio.
# Ninguna respuesta revela si un correo tiene cuenta. Nunca se registran tokens ni contrasenas.
# =========================================================
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from app.core.constants import (
    CORREO_CONTRASENA_CAMBIADA,
    CORREO_RESTABLECER,
    PROPOSITO_RESTABLECER,
    RECUPERACION_ESPERA_SEGUNDOS,
    VIGENCIA_CODIGO_MIN,
)
from app.core.errors import ReglaNegocio
from app.repositories.base import AbrirSesion, RepositorioCuentas
from app.services.codigo_service import CodigoService
from app.services.verificacion_service import EnviadorDeCorreo

MENSAJE_ENLACE_INVALIDO = "El enlace ya se usó o venció. Pide uno nuevo."
RUTA_RESTABLECER = "/restablecer"

# Colombia no tiene horario de verano (UTC-5 todo el año). Evita depender de la base de zonas
# horarias del sistema, que Windows no trae.
ZONA_BOGOTA = timezone(timedelta(hours=-5))
MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def fecha_para_correo(momento: datetime) -> str:
    """'24 de octubre de 2026, 3:05 p. m.' en hora de Colombia."""
    local = momento.astimezone(ZONA_BOGOTA)
    hora = local.hour % 12 or 12
    meridiano = "a. m." if local.hour < 12 else "p. m."  # noqa: PLR2004 - mediodia
    mes = MESES[local.month - 1]
    return f"{local.day} de {mes} de {local.year}, {hora}:{local.minute:02d} {meridiano}"


class RecuperacionService:
    def __init__(  # noqa: PLR0913 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        cuentas: RepositorioCuentas,
        codigos: CodigoService,
        correo: EnviadorDeCorreo,
        *,
        origen_frontend: str,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._cuentas = cuentas
        self._codigos = codigos
        self._correo = correo
        self._origen_frontend = origen_frontend

    def pedir_enlace(self, email: str) -> None:
        """No devuelve nada: quien llama no puede distinguir si el correo tiene cuenta."""
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.buscar_verificada_por_email(sesion, email)
            if cuenta is None or self._codigos.hay_espera(
                sesion, cuenta["id"], PROPOSITO_RESTABLECER, segundos=RECUPERACION_ESPERA_SEGUNDOS
            ):
                return
            token = self._codigos.emitir_token(sesion, cuenta["id"], PROPOSITO_RESTABLECER, email)
        # El token va en el FRAGMENTO (#): el navegador no lo envia al servidor del frontend
        # ni en el Referer.
        enlace = f"{self._origen_frontend}{RUTA_RESTABLECER}#token={token}"
        self._correo.enviar(
            CORREO_RESTABLECER,
            email,
            {
                "nombre": cuenta["nombre"],
                "enlace": enlace,
                "minutos": VIGENCIA_CODIGO_MIN[PROPOSITO_RESTABLECER],
            },
            usuario_id=cuenta["id"],
        )

    def restablecer(self, token: str, password: str) -> None:
        aviso: dict[str, Any] | None = None
        with self._abrir_sesion() as sesion:
            usuario_id = self._codigos.consumir_token(sesion, PROPOSITO_RESTABLECER, token)
            if usuario_id is not None:
                aviso = self._cuentas.datos_de_aviso(sesion, usuario_id)
                # Si algo falla de aqui en adelante, la transaccion se deshace completa y el
                # enlace sigue sirviendo: no se consume un token sin cambiar la contrasena.
                self._cuentas.fijar_contrasena(sesion, usuario_id, password)
                self._cuentas.cerrar_sesiones(sesion, usuario_id)
        if usuario_id is None or aviso is None:
            raise ReglaNegocio(MENSAJE_ENLACE_INVALIDO)
        self._correo.enviar(
            CORREO_CONTRASENA_CAMBIADA,
            aviso["email"],
            {"nombre": aviso["nombre"], "fecha": fecha_para_correo(datetime.now(UTC))},
            usuario_id=usuario_id,
        )
