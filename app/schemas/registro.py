import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LARGO_MAXIMO_EMAIL = 254


class _Cuenta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=LARGO_MAXIMO_EMAIL)

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, valor: object) -> object:
        return " ".join(valor.split()) if isinstance(valor, str) else valor

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, valor: object) -> object:
        if not isinstance(valor, str):
            return valor
        valor = valor.strip().lower()
        if not PATRON_EMAIL.match(valor):
            raise PydanticCustomError("valor_invalido", "El correo no es válido.")
        return valor


class RegistroIn(_Cuenta):
    """Registro de estudiante (HU-B-318)."""

    # La contrasena NO se recorta ni se normaliza: se envia tal cual a Supabase.
    password: str = Field(min_length=8, max_length=72)
    acepta_terminos: bool

    @field_validator("password")
    @classmethod
    def contrasena_segura(cls, valor: str) -> str:
        if not (re.search(r"[A-Za-z]", valor) and re.search(r"\d", valor)):
            raise PydanticCustomError(
                "valor_invalido", "La contraseña debe tener letras y números."
            )
        return valor

    @field_validator("acepta_terminos")
    @classmethod
    def exigir_terminos(cls, valor: bool) -> bool:
        if not valor:
            raise PydanticCustomError("valor_invalido", "Debes aceptar los términos y condiciones.")
        return valor


class InvitacionDocenteIn(_Cuenta):
    """Invitacion de un docente por parte de un administrador (HU-B-318)."""
