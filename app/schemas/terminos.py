from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from app.core.constants import TERMINOS_MAX


class TerminosEditarIn(BaseModel):
    """PUT /admin/terminos: el texto en Markdown y si es una version nueva (todos deben volver
    a aceptarla) o una correccion menor (nadie tiene que hacer nada)."""

    model_config = ConfigDict(extra="forbid")

    contenido: str = Field(max_length=TERMINOS_MAX)
    nueva_version: StrictBool

    @field_validator("contenido")
    @classmethod
    def no_vacio(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("Escribe el texto de los términos.")
        return texto


class AceptarTerminosIn(BaseModel):
    """POST /me/terminos: la version que la persona leyo. Si ya hay otra, 409."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
