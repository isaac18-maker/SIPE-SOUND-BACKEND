import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from app.core.longitudes import EMAIL_MAX

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_email(valor: object) -> object:
    """Recorta y pasa a minusculas; rechaza lo que no tenga forma de correo."""
    if not isinstance(valor, str):
        return valor
    valor = valor.strip().lower()
    if not PATRON_EMAIL.match(valor):
        raise PydanticCustomError("valor_invalido", "El correo no es válido.")
    return valor


class PreautorizacionDocenteIn(BaseModel):
    """Correo que un administrador autoriza como docente (HU-B-321)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=EMAIL_MAX)

    @field_validator("email", mode="before")
    @classmethod
    def normalizar(cls, valor: object) -> object:
        return normalizar_email(valor)
