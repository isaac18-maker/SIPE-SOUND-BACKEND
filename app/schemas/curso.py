from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import LARGO_CODIGO

MAXIMO_BLOQUES_EN_RUTA = 100


class CursoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    nivel: Literal["principiante", "intermedio", "avanzado"] = "principiante"


class UnirseCursoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=LARGO_CODIGO, max_length=LARGO_CODIGO)

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar(cls, valor: object) -> object:
        """El estudiante puede escribirlo en minusculas o con espacios."""
        return valor.strip().upper() if isinstance(valor, str) else valor


class BloqueEnRuta(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    bloque_id: int = Field(gt=0)
    orden: int = Field(gt=0)


class RutaCursoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bloques: list[BloqueEnRuta] = Field(max_length=MAXIMO_BLOQUES_EN_RUTA)

    @model_validator(mode="after")
    def sin_repetidos(self) -> "RutaCursoIn":
        bloques = [b.bloque_id for b in self.bloques]
        ordenes = [b.orden for b in self.bloques]
        if len(set(bloques)) != len(bloques):
            raise ValueError("un bloque no puede aparecer dos veces en la ruta")
        if len(set(ordenes)) != len(ordenes):
            raise ValueError("dos bloques no pueden tener el mismo orden")
        return self
