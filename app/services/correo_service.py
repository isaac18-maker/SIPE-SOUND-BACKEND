# =========================================================
# Correos transaccionales (HU-B-401): codigos, enlaces y avisos de seguridad.
# Cada tipo tiene su plantilla en app/templates/correo/ (HTML + texto plano) y su asunto
# aqui. El envio sale en segundo plano para no retrasar la respuesta de la API, y el
# resultado queda en envios_correo. Nunca se registran codigos, enlaces ni cuerpos.
# =========================================================
import logging
from concurrent.futures import Executor
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.core.constants import (
    CORREO_CAMBIAR_CORREO,
    CORREO_CONTRASENA_CAMBIADA,
    CORREO_CORREO_CAMBIADO,
    CORREO_REAUTENTICACION,
    CORREO_RESTABLECER,
    CORREO_VERIFICAR,
    ENVIO_ENVIADO,
    ENVIO_FALLIDO,
)
from app.core.errors import EnvioCorreoFallido
from app.repositories.base import AbrirSesion, RepositorioEnviosCorreo

logger = logging.getLogger(__name__)

DIRECTORIO_PLANTILLAS = Path(__file__).resolve().parent.parent / "templates" / "correo"
MARCA = "SIPE-SOUND"
# Logo de la cabecera: viaja dentro del correo (cid:logo) para verse sin una URL publica.
RUTA_LOGO = DIRECTORIO_PLANTILLAS / "logo.png"

# Asunto por tipo. El codigo va en el asunto: se ve en la notificacion del celular.
ASUNTOS = {
    CORREO_VERIFICAR: "Tu código de SIPE-SOUND: {codigo}",
    CORREO_REAUTENTICACION: "Confirma que eres tú: {codigo}",
    CORREO_RESTABLECER: "Crea una contraseña nueva en SIPE-SOUND",
    CORREO_CONTRASENA_CAMBIADA: "Tu contraseña de SIPE-SOUND cambió",
    CORREO_CAMBIAR_CORREO: "Confirma tu correo nuevo: {codigo}",
    CORREO_CORREO_CAMBIADO: "El correo de tu cuenta de SIPE-SOUND cambió",
}


class Enviador(Protocol):
    """Lo cumplen EnviadorSmtp y EnviadorArchivo (app/infrastructure/correo_smtp.py)."""

    def enviar(self, mensaje: EmailMessage) -> None: ...


def crear_plantillas() -> Environment:
    # Solo el HTML se escapa. StrictUndefined: una variable que falta es un error, no un
    # correo con un hueco ("Tu codigo es: ").
    return Environment(
        loader=FileSystemLoader(DIRECTORIO_PLANTILLAS),
        autoescape=select_autoescape(enabled_extensions=("html",), default=False),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


class CorreoService:
    def __init__(  # noqa: PLR0913 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        registro: RepositorioEnviosCorreo,
        enviador: Enviador,
        ejecutor: Executor,
        *,
        remitente: str,
        nombre_remitente: str = MARCA,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._registro = registro
        self._enviador = enviador
        self._ejecutor = ejecutor
        self._remitente = remitente
        self._nombre_remitente = nombre_remitente
        self._plantillas = crear_plantillas()
        self._logo = RUTA_LOGO.read_bytes()

    def enviar(
        self,
        tipo: str,
        destinatario: str,
        contexto: dict[str, Any],
        usuario_id: str | None = None,
    ) -> None:
        """Arma el correo ahora (un error de plantilla se ve de inmediato) y lo envia en
        segundo plano. Un fallo de envio no interrumpe a quien lo pidio: queda registrado."""
        mensaje = self._armar(tipo, destinatario, contexto)
        self._ejecutor.submit(self._entregar, mensaje, tipo, usuario_id)

    def enviar_ahora(
        self,
        tipo: str,
        destinatario: str,
        contexto: dict[str, Any],
        usuario_id: str | None = None,
    ) -> str | None:
        """Igual que enviar, pero espera. Devuelve None si salio o el codigo del fallo."""
        return self._entregar(self._armar(tipo, destinatario, contexto), tipo, usuario_id)

    def _armar(self, tipo: str, destinatario: str, contexto: dict[str, Any]) -> EmailMessage:
        if tipo not in ASUNTOS:
            raise ValueError(f"Tipo de correo desconocido: {tipo}")
        datos = {**contexto, "marca": MARCA, "asunto": ASUNTOS[tipo].format(**contexto)}
        mensaje = EmailMessage()
        mensaje["Subject"] = datos["asunto"]
        mensaje["From"] = formataddr((self._nombre_remitente, self._remitente))
        mensaje["To"] = destinatario
        mensaje["Date"] = formatdate(usegmt=True)
        mensaje["Message-ID"] = make_msgid(domain=self._remitente.rpartition("@")[2])
        mensaje["Auto-Submitted"] = "auto-generated"
        # Texto plano primero y HTML despues: el cliente muestra la ultima parte que entiende.
        mensaje.set_content(self._plantillas.get_template(f"{tipo}.txt").render(**datos))
        mensaje.add_alternative(
            self._plantillas.get_template(f"{tipo}.html").render(**datos), subtype="html"
        )
        mensaje.get_payload()[-1].add_related(
            self._logo, maintype="image", subtype="png", cid="<logo>", filename="logo.png"
        )
        return mensaje

    def _entregar(self, mensaje: EmailMessage, tipo: str, usuario_id: str | None) -> str | None:
        error: str | None = None
        try:
            self._enviador.enviar(mensaje)
        except EnvioCorreoFallido as fallo:
            error = fallo.codigo
            logger.warning("Correo '%s' no enviado: %s", tipo, error)
        self._registrar(tipo, usuario_id, error)
        return error

    def _registrar(self, tipo: str, usuario_id: str | None, error: str | None) -> None:
        try:
            with self._abrir_sesion() as sesion:
                self._registro.registrar(
                    sesion,
                    usuario_id=usuario_id,
                    tipo=tipo,
                    estado=ENVIO_ENVIADO if error is None else ENVIO_FALLIDO,
                    error=error,
                )
        except Exception:
            # El correo ya salio (o fallo): perder la bitacora no debe tumbar el hilo.
            logger.exception("No se pudo registrar el envio del correo '%s'", tipo)
