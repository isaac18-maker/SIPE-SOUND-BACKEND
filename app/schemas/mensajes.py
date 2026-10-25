from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    model_validator,
)

from app.core.longitudes import (
    ASUNTO_MAX,
    ASUNTO_MIN,
    BUSQUEDA_MAX,
    CUERPO_MENSAJE_MAX,
    CUERPO_MENSAJE_MIN,
    POR_PAGINA_MAX,
)
from app.schemas.contenido import Busqueda

Alcance = Literal[
    "usuario",
    "curso",
    "estudiantes_docente",
    "rol_estudiante",
    "rol_docente",
    "rol_admin",
    "todos",
]
Asunto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=ASUNTO_MIN, max_length=ASUNTO_MAX)
]
Cuerpo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=CUERPO_MENSAJE_MIN, max_length=CUERPO_MENSAJE_MAX
    ),
]
BusquedaDestinatario = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=BUSQUEDA_MAX)
]


class SolicitudNombreIn(BaseModel):
    """POST /me/solicitud-nombre: solo el texto; el destino y el asunto los fija la API."""

    model_config = ConfigDict(extra="forbid")

    cuerpo: Cuerpo


class MensajeCrearIn(BaseModel):
    """Un mensaje nuevo (alcance, asunto) o la respuesta a uno recibido (respuesta_a_id)."""

    model_config = ConfigDict(extra="forbid")

    alcance: Alcance | None = None
    destinatario_id: UUID | None = None
    curso_id: int | None = Field(default=None, gt=0)
    asunto: Asunto | None = None
    cuerpo: Cuerpo
    respuesta_a_id: UUID | None = None

    @model_validator(mode="after")
    def coherencia(self) -> Self:
        if self.respuesta_a_id is not None:
            # Una respuesta toma destino, alcance y asunto del mensaje original.
            if self.alcance or self.destinatario_id or self.curso_id or self.asunto:
                raise ValueError(
                    "Al responder solo se envía el cuerpo: "
                    "el destino y el asunto son los del mensaje."
                )
            return self
        if self.alcance is None:
            raise ValueError("Indica a quién va el mensaje (alcance).")
        if self.asunto is None:
            raise ValueError("Escribe un asunto.")
        if self.alcance == "usuario" and self.destinatario_id is None:
            raise ValueError("Indica la persona (destinatario_id).")
        if self.alcance == "curso" and self.curso_id is None:
            raise ValueError("Indica el curso (curso_id).")
        if self.alcance != "usuario" and self.destinatario_id is not None:
            raise ValueError("destinatario_id solo se usa cuando el alcance es 'usuario'.")
        if self.alcance != "curso" and self.curso_id is not None:
            raise ValueError("curso_id solo se usa cuando el alcance es 'curso'.")
        return self

    def datos(self) -> dict:
        return {
            "alcance": self.alcance,
            "destinatario_id": str(self.destinatario_id) if self.destinatario_id else None,
            "curso_id": self.curso_id,
            "asunto": self.asunto,
            "cuerpo": self.cuerpo,
            "respuesta_a_id": str(self.respuesta_a_id) if self.respuesta_a_id else None,
        }


class FiltrosBandeja(BaseModel):
    """?filtro=recibidos|enviados|no_leidos|archivados&q=&pagina=&por_pagina="""

    model_config = ConfigDict(extra="forbid")

    filtro: Literal["recibidos", "enviados", "no_leidos", "archivados"] = "recibidos"
    q: Busqueda | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class HiloEditarIn(BaseModel):
    """{archivado: bool} y/o {leido: bool}. `leido: false` deja el ultimo recibido sin leer."""

    model_config = ConfigDict(extra="forbid")

    archivado: StrictBool | None = None
    leido: StrictBool | None = None

    @model_validator(mode="after")
    def exigir_algo(self) -> Self:
        if self.archivado is None and self.leido is None:
            raise ValueError("Envía archivado, leido o ambos.")
        return self


class BuscarDestinatariosQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: BusquedaDestinatario | None = None
