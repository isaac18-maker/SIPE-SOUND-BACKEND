import re

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from pydantic_core import PydanticCustomError

from app.core.longitudes import (
    EMAIL_MAX,
    NOMBRE_PERSONA_MAX,
    NOMBRE_PERSONA_MIN,
    PASSWORD_MAX,
    PASSWORD_MIN,
)

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_CODIGO = re.compile(r"\d{6}")
PATRON_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")  # secrets.token_urlsafe(32)
# Letras (con tildes y ene), separadas por espacio, apostrofo, punto o guion: "Ana María", "O'Neil".
PATRON_NOMBRE = re.compile(r"[^\W\d_]+(?:[ '.\-]+[^\W\d_]+)*\.?")


def _exigir_letras_y_numeros(valor: str) -> str:
    if not (re.search(r"[A-Za-z]", valor) and re.search(r"\d", valor)):
        raise PydanticCustomError("valor_invalido", "La contraseña debe tener letras y números.")
    return valor


def _normalizar_email(valor: object) -> object:
    if not isinstance(valor, str):
        return valor
    valor = valor.strip().lower()
    if not PATRON_EMAIL.match(valor):
        raise PydanticCustomError("valor_invalido", "El correo no es válido.")
    return valor


class InicioSesionIn(BaseModel):
    """Inicio de sesion (HU-B-322). Sin minimo de contrasena: cuentas antiguas."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=EMAIL_MAX)
    # La contrasena NO se recorta ni se normaliza: se envia tal cual a Supabase.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)

    _email = field_validator("email", mode="before")(_normalizar_email)


class ReenvioVerificacionIn(BaseModel):
    """Pedir otro codigo de verificacion (HU-B-402)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=EMAIL_MAX)

    _email = field_validator("email", mode="before")(_normalizar_email)


class OlvidoContrasenaIn(ReenvioVerificacionIn):
    """Pedir el enlace para restablecer la contrasena (HU-B-403)."""


class RestablecerContrasenaIn(BaseModel):
    """Token del enlace + contrasena nueva (mismas reglas que el registro)."""

    model_config = ConfigDict(extra="forbid")

    token: str
    # La contrasena NO se recorta ni se normaliza.
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    _password = field_validator("password")(_exigir_letras_y_numeros)

    @field_validator("token", mode="before")
    @classmethod
    def limpiar_token(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("token")
    @classmethod
    def formato_token(cls, valor: str) -> str:
        if not PATRON_TOKEN.fullmatch(valor):
            raise PydanticCustomError("valor_invalido", "El enlace no es válido. Pide uno nuevo.")
        return valor


class VerificacionIn(ReenvioVerificacionIn):
    """Correo + codigo de 6 digitos (se aceptan espacios: "482 913")."""

    codigo: str

    @field_validator("codigo", mode="before")
    @classmethod
    def limpiar_codigo(cls, valor: object) -> object:
        return "".join(valor.split()) if isinstance(valor, str) else valor

    @field_validator("codigo")
    @classmethod
    def solo_digitos(cls, valor: str) -> str:
        if not PATRON_CODIGO.fullmatch(valor):
            raise PydanticCustomError("valor_invalido", "El código tiene 6 dígitos.")
        return valor


class RegistroIn(BaseModel):
    """Registro de estudiante o de docente preautorizado (HU-B-322)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=NOMBRE_PERSONA_MIN, max_length=NOMBRE_PERSONA_MAX)
    email: str = Field(max_length=EMAIL_MAX)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    # Consentimiento (Ley 1581 de 2012): la API no crea cuentas sin él (HU-B-323).
    acepta_terminos: StrictBool

    _email = field_validator("email", mode="before")(_normalizar_email)

    @field_validator("acepta_terminos")
    @classmethod
    def exigir_terminos(cls, valor: bool) -> bool:
        if not valor:
            raise PydanticCustomError("valor_invalido", "Debes aceptar los términos y condiciones.")
        return valor

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, valor: object) -> object:
        return " ".join(valor.split()) if isinstance(valor, str) else valor

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        if not PATRON_NOMBRE.fullmatch(valor):
            raise PydanticCustomError(
                "valor_invalido", "Usa solo letras, espacios, apóstrofo, punto o guion."
            )
        return valor

    _password = field_validator("password")(_exigir_letras_y_numeros)
