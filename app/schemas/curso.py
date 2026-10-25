from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.core.constants import ALFABETO_CODIGO, LARGO_CODIGO
from app.core.longitudes import (
    MENSAJE_RETROALIMENTACION_MAX,
    MENSAJE_RETROALIMENTACION_MIN,
    POR_PAGINA_MAX,
)
from app.schemas.contenido import Busqueda, Descripcion, EntradaEditable, Nivel, Titulo

MAXIMO_BLOQUES_EN_RUTA = 100


class CursoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Titulo
    descripcion: Descripcion | None = None
    nivel: Nivel = "principiante"


class MisCursosQuery(BaseModel):
    """GET /cursos (HU-B-502): filtro por estado y orden (ultimo avance, nombre o avance)."""

    model_config = ConfigDict(extra="forbid")

    estado: Literal["sin_iniciar", "en_curso", "finalizado"] | None = None
    orden: Literal["ultimo_avance", "nombre", "avance"] = "ultimo_avance"


class UnirseCursoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=LARGO_CODIGO, max_length=LARGO_CODIGO)

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar(cls, valor: object) -> object:
        """El estudiante puede escribirlo en minusculas o con espacios."""
        return valor.strip().upper() if isinstance(valor, str) else valor

    @field_validator("codigo")
    @classmethod
    def validar_alfabeto(cls, valor: str) -> str:
        if any(letra not in ALFABETO_CODIGO for letra in valor):
            raise PydanticCustomError(
                "valor_invalido", "El código solo tiene letras y números (sin 0, O, 1, I ni L)."
            )
        return valor


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


# --- Panel docente (HU-B-310) -----------------------------------------------
class CursoEditar(EntradaEditable):
    NO_NULOS = ("nombre", "nivel")

    nombre: Titulo | None = None
    descripcion: Descripcion | None = None
    nivel: Nivel | None = None


class RetroalimentacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensaje: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=MENSAJE_RETROALIMENTACION_MIN,
            max_length=MENSAJE_RETROALIMENTACION_MAX,
        ),
    ]


class CursosQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["activo", "archivado"] = "activo"


class EstudiantesQuery(BaseModel):
    """?q=&orden=-avance_pct|nombre|-ultimo_avance&pagina=&por_pagina=."""

    model_config = ConfigDict(extra="forbid")

    q: Busqueda | None = None
    orden: Literal["nombre", "-avance_pct", "-ultimo_avance"] = "nombre"
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)
