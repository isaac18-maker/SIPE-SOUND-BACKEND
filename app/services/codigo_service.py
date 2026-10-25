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

TOKEN_BYTES = 32


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
        return self.consumir_completo(sesion, usuario_id, proposito, codigo) is not None

    def consumir_completo(
        self, sesion: Any, usuario_id: str, proposito: str, codigo: str
    ) -> dict[str, Any] | None:
        """Como consumir, pero devuelve la fila del codigo (p. ej. su email_destino) o None."""
        abierto = self._codigos.obtener_abierto_vigente(sesion, usuario_id, proposito)
        if abierto is None:
            return None
        esperado = self._hash(usuario_id, proposito, codigo)
        if not hmac.compare_digest(abierto["codigo_hash"], esperado):
            self._codigos.registrar_fallo(sesion, abierto["id"])
            return None
        return abierto if self._codigos.consumir(sesion, abierto["id"]) else None

    def emitir_token(  # noqa: PLR0913
        self,
        sesion: Any,
        usuario_id: str,
        proposito: str,
        email_destino: str | None = None,
        *,
        ambito: str = "",
    ) -> str:
        """Token largo (32 bytes, 43 caracteres base64url). Es inadivinable, asi que no cuenta
        intentos: se busca por su hash y el propio token identifica a la persona.

        `ambito` ata el token a algo mas (p. ej. la sesion): sin el mismo ambito al consumirlo,
        el hash no coincide y el token no sirve."""
        token = secrets.token_urlsafe(TOKEN_BYTES)
        self._codigos.invalidar_abiertos(sesion, usuario_id, proposito)
        self._codigos.crear(
            sesion,
            usuario_id=usuario_id,
            proposito=proposito,
            codigo_hash=self._hash_token(proposito, token, ambito),
            email_destino=email_destino,
            vigencia_min=VIGENCIA_CODIGO_MIN[proposito],
        )
        return token

    def consumir_token(
        self, sesion: Any, proposito: str, token: str, *, ambito: str = ""
    ) -> str | None:
        """Id de la persona dueña del token si era el vigente (y ya no podra usarse otra vez);
        None si no existe, vencio, fue reemplazado o ya se uso."""
        abierto = self._codigos.obtener_abierto_por_hash(
            sesion, proposito, self._hash_token(proposito, token, ambito)
        )
        if abierto is None or not self._codigos.consumir(sesion, abierto["id"]):
            return None
        return abierto["usuario_id"]

    def hay_espera(
        self,
        sesion: Any,
        usuario_id: str,
        proposito: str,
        *,
        segundos: int = CODIGO_ESPERA_SEGUNDOS,
    ) -> bool:
        """True si ya se emitio uno hace menos de `segundos` (limite por cuenta)."""
        return self._codigos.hay_reciente(sesion, usuario_id, proposito, segundos=segundos)

    def _hash_token(self, proposito: str, token: str, ambito: str = "") -> str:
        # Sin usuario_id: el token es lo unico que llega en el enlace. El proposito y el
        # ambito (p. ej. la sesion) si van.
        mensaje = f"{proposito}:{ambito}:{token}".encode()
        return hmac.new(self._secreto, mensaje, hashlib.sha256).hexdigest()

    def _hash(self, usuario_id: str, proposito: str, codigo: str) -> str:
        # El proposito y la persona van dentro del hash: un codigo no sirve para otro fin.
        mensaje = f"{proposito}:{usuario_id}:{codigo}".encode()
        return hmac.new(self._secreto, mensaje, hashlib.sha256).hexdigest()
