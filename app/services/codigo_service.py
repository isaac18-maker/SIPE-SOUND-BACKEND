# =========================================================
# Codigos de un solo uso (HU-B-402). Reutilizable por la verificacion de correo (B-402),
# el restablecimiento de contrasena (B-403) y el cambio de correo y contrasena (B-404).
#   - Solo se guarda el HMAC-SHA256 del codigo, atado al proposito y a la persona.
#   - Un codigo nuevo invalida el anterior; vence en <= 15 minutos; se consume una sola vez.
#   - Tras 5 intentos fallidos el codigo se invalida.
# Opera dentro de la sesion de quien lo llama (unidad de trabajo): el llamador confirma.
# Nunca se registran codigos en logs.
# =========================================================
import hashlib
import hmac
import secrets
from typing import Any

from app.core.constants import (
    CODIGO_DIGITOS,
    CODIGO_ESPERA_SEGUNDOS,
    VIGENCIA_CODIGO_MIN,
)
from app.repositories.base import RepositorioCodigos


class CodigoService:
    def __init__(self, codigos: RepositorioCodigos, secreto: bytes) -> None:
        self._codigos = codigos
        self._secreto = secreto

    def emitir(
        self, sesion: Any, usuario_id: str, proposito: str, email_destino: str | None = None
    ) -> str:
        """Invalida el codigo abierto de este proposito y crea uno nuevo. Devuelve el valor
        en claro SOLO para enviarlo por correo: en la base queda su hash."""
        codigo = f"{secrets.randbelow(10**CODIGO_DIGITOS):0{CODIGO_DIGITOS}d}"
        self._codigos.invalidar_abiertos(sesion, usuario_id, proposito)
        self._codigos.crear(
            sesion,
            usuario_id=usuario_id,
            proposito=proposito,
            codigo_hash=self._hash(usuario_id, proposito, codigo),
            email_destino=email_destino,
            vigencia_min=VIGENCIA_CODIGO_MIN[proposito],
        )
        return codigo

    def consumir(self, sesion: Any, usuario_id: str, proposito: str, codigo: str) -> bool:
        """True si el codigo era el vigente y ya no podra usarse otra vez.

        Devuelve False (no lanza) ante un codigo errado para que el llamador confirme la
        transaccion: el intento fallido tiene que quedar contado.
        """
        abierto = self._codigos.obtener_abierto_vigente(sesion, usuario_id, proposito)
        if abierto is None:
            return False
        esperado = self._hash(usuario_id, proposito, codigo)
        if not hmac.compare_digest(abierto["codigo_hash"], esperado):
            self._codigos.registrar_fallo(sesion, abierto["id"])
            return False
        return self._codigos.consumir(sesion, abierto["id"])

    def hay_espera(self, sesion: Any, usuario_id: str, proposito: str) -> bool:
        """True si ya se emitio uno hace menos de un minuto (limite por cuenta)."""
        return self._codigos.hay_reciente(
            sesion, usuario_id, proposito, segundos=CODIGO_ESPERA_SEGUNDOS
        )

    def _hash(self, usuario_id: str, proposito: str, codigo: str) -> str:
        # El proposito y la persona van dentro del hash: un codigo no sirve para otro fin.
        mensaje = f"{proposito}:{usuario_id}:{codigo}".encode()
        return hmac.new(self._secreto, mensaje, hashlib.sha256).hexdigest()
