from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class VerificarQuizIn(BaseModel):
    # id_pregunta (texto) -> indice elegido
    respuestas: Any = Field(default=None, validate_default=True)

    @field_validator("respuestas", mode="before")
    @classmethod
    def validar_respuestas(cls, valor: Any) -> dict[str, Any]:
        if valor is None:
            raise PydanticCustomError("valor_invalido", "Falta el campo 'respuestas'")
        if not isinstance(valor, dict):
            raise PydanticCustomError("valor_invalido", "El campo 'respuestas' debe ser un objeto")
        return valor
