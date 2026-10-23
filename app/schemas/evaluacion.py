from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.core.constants import PORCENTAJE_APROBACION
from app.core.longitudes import (
    APROBACION_MAX,
    APROBACION_MIN,
    ENUNCIADO_MAX,
    ENUNCIADO_MIN,
    INTENTOS_MAX_MAX,
    INTENTOS_MAX_MIN,
    OPCION_MAX,
    OPCION_MIN,
    OPCIONES_MAX,
    OPCIONES_MIN,
    PREGUNTAS_MAX,
    PREGUNTAS_MIN,
)
from app.schemas.contenido import Descripcion, EntradaEditable, Titulo


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


# --- Panel docente (HU-B-311) -----------------------------------------------
_LARGO_ENUNCIADO = {"min_length": ENUNCIADO_MIN, "max_length": ENUNCIADO_MAX}
Enunciado = Annotated[str, StringConstraints(strip_whitespace=True, **_LARGO_ENUNCIADO)]
Opcion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=OPCION_MIN, max_length=OPCION_MAX)
]
Aprobacion = Annotated[int, Field(ge=APROBACION_MIN, le=APROBACION_MAX)]
IntentosMax = Annotated[int, Field(ge=INTENTOS_MAX_MIN, le=INTENTOS_MAX_MAX)]


def _fecha_futura(valor: datetime | None) -> datetime | None:
    if valor is not None and valor <= datetime.now(UTC):
        raise PydanticCustomError("valor_invalido", "La fecha límite debe ser futura.")
    return valor


FechaLimite = Annotated[AwareDatetime, AfterValidator(_fecha_futura)]


class EvaluacionCrear(EntradaEditable):
    titulo: Titulo
    descripcion: Descripcion | None = None
    curso_id: int | None = Field(default=None, gt=0)
    bloque_id: int | None = Field(default=None, gt=0)
    porcentaje_aprobacion: Aprobacion = PORCENTAJE_APROBACION
    intentos_max: IntentosMax | None = None
    fecha_limite: FechaLimite | None = None

    @model_validator(mode="after")
    def curso_o_bloque(self) -> "EvaluacionCrear":
        if self.curso_id is None and self.bloque_id is None:
            raise PydanticCustomError("valor_invalido", "Indica curso_id o bloque_id.")
        return self


class EvaluacionEditar(EntradaEditable):
    NO_NULOS = ("titulo", "porcentaje_aprobacion")

    titulo: Titulo | None = None
    descripcion: Descripcion | None = None
    porcentaje_aprobacion: Aprobacion | None = None
    intentos_max: IntentosMax | None = None
    fecha_limite: FechaLimite | None = None


class PreguntaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enunciado: Enunciado
    opciones: Annotated[list[Opcion], Field(min_length=OPCIONES_MIN, max_length=OPCIONES_MAX)]
    respuesta_correcta: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def coherente(self) -> "PreguntaIn":
        if len({o.lower() for o in self.opciones}) != len(self.opciones):
            raise PydanticCustomError("valor_invalido", "Hay opciones repetidas.")
        if self.respuesta_correcta >= len(self.opciones):
            raise PydanticCustomError(
                "valor_invalido", "respuesta_correcta debe ser el índice de una opción."
            )
        return self


class PreguntasIn(BaseModel):
    """PUT /docente/evaluaciones/{id}/preguntas: reemplaza el conjunto completo."""

    model_config = ConfigDict(extra="forbid")

    preguntas: Annotated[
        list[PreguntaIn], Field(min_length=PREGUNTAS_MIN, max_length=PREGUNTAS_MAX)
    ]


class EstadoEvaluacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["borrador", "publicada", "cerrada"]


class FiltrosEvaluaciones(BaseModel):
    model_config = ConfigDict(extra="forbid")

    curso_id: int | None = Field(default=None, gt=0)
    estado: Literal["borrador", "publicada", "cerrada"] | None = None
