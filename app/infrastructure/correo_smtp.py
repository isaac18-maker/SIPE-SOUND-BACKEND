# =========================================================
# Envio de correo (HU-B-401). Dos implementaciones del mismo contrato:
#   - EnviadorSmtp: smtp.gmail.com:587 con STARTTLS y contrasena de aplicacion.
#   - EnviadorArchivo: escribe un .eml en tmp/correos/ (solo APP_ENV=local).
# Libreria estandar (smtplib): sin dependencias nuevas.
# Nunca se registran la clave, la direccion ni el contenido del correo.
# =========================================================
import smtplib
import ssl
import uuid
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from app.core.errors import EnvioCorreoFallido

TIMEOUT_SEGUNDOS = 15
DIRECTORIO_CORREOS = Path(__file__).resolve().parents[2] / "tmp" / "correos"

ERRORES_RECHAZO = (
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPDataError,
    smtplib.SMTPHeloError,
)
ERRORES_CONEXION = (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)


class EnviadorSmtp:
    def __init__(self, *, host: str, puerto: int, usuario: str, clave: str) -> None:
        self._host = host
        self._puerto = puerto
        self._usuario = usuario
        # Google muestra la contrasena de aplicacion en grupos de 4 separados por espacios.
        self._clave = clave.replace(" ", "")

    def enviar(self, mensaje: EmailMessage) -> None:
        contexto = ssl.create_default_context()
        try:
            with smtplib.SMTP(self._host, self._puerto, timeout=TIMEOUT_SEGUNDOS) as servidor:
                servidor.starttls(context=contexto)
                servidor.login(self._usuario, self._clave)
                servidor.send_message(mensaje)
        except smtplib.SMTPAuthenticationError:
            raise EnvioCorreoFallido("smtp_auth") from None
        except ERRORES_RECHAZO:
            raise EnvioCorreoFallido("smtp_rechazado") from None
        except ERRORES_CONEXION:
            raise EnvioCorreoFallido("smtp_conexion") from None
        except smtplib.SMTPException:
            raise EnvioCorreoFallido("smtp_error") from None
        except TimeoutError:
            raise EnvioCorreoFallido("smtp_timeout") from None
        except ssl.SSLError:
            raise EnvioCorreoFallido("smtp_tls") from None
        except OSError:
            raise EnvioCorreoFallido("smtp_conexion") from None


class EnviadorArchivo:
    """Para desarrollo sin cuenta de Gmail: cada correo queda como un .eml que se abre en
    cualquier cliente de correo."""

    def __init__(self, directorio: Path = DIRECTORIO_CORREOS) -> None:
        self._directorio = directorio

    def enviar(self, mensaje: EmailMessage) -> None:
        try:
            self._directorio.mkdir(parents=True, exist_ok=True)
            marca = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            ruta = self._directorio / f"{marca}-{uuid.uuid4().hex[:8]}.eml"
            ruta.write_bytes(mensaje.as_bytes())
        except OSError:
            raise EnvioCorreoFallido("archivo_error") from None
