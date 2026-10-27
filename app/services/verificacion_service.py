# =========================================================
# Verificacion del correo con un codigo propio (HU-B-402).
# El registro SI dice si el correo ya tiene cuenta o un registro en curso (HU-B-416): asi la
# persona sabe si iniciar sesion o pedir otro codigo. Reenviar y verificar siguen respondiendo
# igual ante un correo inexistente, un codigo errado, vencido o usado.
# =========================================================
from typing import Any, Protocol

from app.core.constants import (
    CORREO_VERIFICAR,
    PROPOSITO_VERIFICAR_CORREO,
    VIGENCIA_CODIGO_MIN,
    VIGENCIA_VERIFICACION_SEGUNDOS,
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

    def estado_de_registro(self, email: str) -> dict[str, Any] | None:
        """None si el correo no tiene cuenta. Si la tiene: `verificada` (ya puede iniciar
        sesion) o `pendiente` (registro en curso), con los segundos que le quedan al codigo."""
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.buscar_por_email(sesion, email)
            if cuenta is None:
                return None
            if cuenta["verificada"]:
                return {"estado": "verificada", "vence_en_segundos": 0}
            restante = self._codigos.segundos_restantes(
                sesion, cuenta["id"], PROPOSITO_VERIFICAR_CORREO
            )
            return {"estado": "pendiente", "vence_en_segundos": restante}

    def enviar_codigo(self, email: str) -> int:
        """Si el correo tiene una cuenta SIN verificar, le envia un codigo nuevo y devuelve los
        segundos que dura. En cualquier otro caso devuelve 0: reenviar no usa el valor y su
        respuesta es la misma exista o no la cuenta."""
        with self._abrir_sesion() as sesion:
            cuenta = self._cuentas.buscar_pendiente_por_email(sesion, email)
            if cuenta is None or self._codigos.hay_espera(
                sesion, cuenta["id"], PROPOSITO_VERIFICAR_CORREO
            ):
                return 0
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
        return VIGENCIA_VERIFICACION_SEGUNDOS

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
