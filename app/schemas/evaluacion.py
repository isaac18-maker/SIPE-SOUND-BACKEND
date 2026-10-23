from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from pydantic_core import PydanticCustomError

from app.core.longitudes import OPCIONES_MAX, PREGUNTAS_MAX


class IntentoIn(BaseModel):
    """POST /evaluaciones/{id}/intentos: {"respuestas": {"<id de pregunta>": <indice>}}."""

    model_config = ConfigDict(extra="forbid")

    respuestas: dict[str, StrictInt] = Field(min_length=1, max_length=PREGUNTAS_MAX)

    @field_validator("respuestas")
    @classmethod
    def validar(cls, respuestas: dict[str, int]) -> dict[str, int]:
        for pregunta, indice in respuestas.items():
            if not pregunta.isdigit():
                raise PydanticCustomError("valor_invalido", "Las claves deben ser ids de pregunta.")
            if not 0 <= indice < OPCIONES_MAX:
                raise PydanticCustomError(
                    "valor_invalido", f"Cada respuesta es un índice entre 0 y {OPCIONES_MAX - 1}."
                )
        return respuestas


class RutaQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    curso_id: int | None = Field(default=None, gt=0)
