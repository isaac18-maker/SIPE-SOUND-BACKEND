# =========================================================
# Verificacion del correo con un codigo propio (HU-B-402).
# Ninguna respuesta revela si un correo tiene cuenta: enviar_codigo no devuelve nada y
# verificar responde igual ante un correo inexistente, un codigo errado, vencido o usado.
# =========================================================
from typing import Any, Protocol

from app.core.constants import (
    CORREO_VERIFICAR,
    PROPOSITO_VERIFICAR_CORREO,
    VIGENCIA_CODIGO_MIN,
)
from app.core.errors import ReglaNegocio
from app.repositories.base import AbrirSesion, RepositorioCuentas
from app.services.codigo_service import CodigoService

MENSAJE_CODIGO_INVALIDO = "El código no es válido o ya venció. Pide uno nuevo."


class EnviadorDeCorreo(Protocol):
    """Lo cumple CorreoService."""

    def enviar(
        self, tipo: str, destinatario: str, contexto: dict[str, Any], usuario_id: str | None = None
    ) -> None: ...


class VerificacionService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        cuentas: RepositorioCuentas,
        codigos: CodigoService,
        correo: EnviadorDeCorreo,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._cuentas = cuentas
        self._codigos = codigos
        self._correo = correo

    def enviar_codigo(self, email: str) -> None:
        """Si el correo tiene una cuenta SIN verificar, le envia un codigo nuevo. En cualquier
        otro caso no hace nada (y quien llama no puede distinguirlo)."""
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.buscar_pendiente_por_email(sesion, email)
            if cuenta is None or self._codigos.hay_espera(
                sesion, cuenta["id"], PROPOSITO_VERIFICAR_CORREO
            ):
                return
            codigo = self._codigos.emitir(sesion, cuenta["id"], PROPOSITO_VERIFICAR_CORREO, email)
        # Despues de confirmar: el correo no puede llegar antes de que el codigo exista.
        self._correo.enviar(
            CORREO_VERIFICAR,
            email,
            {
                "nombre": cuenta["nombre"],
                "codigo": codigo,
                "minutos": VIGENCIA_CODIGO_MIN[PROPOSITO_VERIFICAR_CORREO],
            },
            usuario_id=cuenta["id"],
        )

    def verificar(self, email: str, codigo: str) -> None:
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.buscar_pendiente_por_email(sesion, email)
            valido = cuenta is not None and self._codigos.consumir(
                sesion, cuenta["id"], PROPOSITO_VERIFICAR_CORREO, codigo
            )
            if valido:
                # El trigger de la base aplica aqui el rol docente si el correo esta preautorizado.
                self._cuentas.marcar_verificada(sesion, cuenta["id"])
        # Fuera del with: un codigo errado debe confirmar el intento fallido, no deshacerlo.
        if not valido:
            raise ReglaNegocio(MENSAJE_CODIGO_INVALIDO)
