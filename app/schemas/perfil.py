from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.core.longitudes import (
    APELLIDO_PERSONA_MAX,
    APELLIDO_PERSONA_MIN,
    NOMBRE_PERSONA_MAX,
    NOMBRE_PERSONA_MIN,
)
from app.schemas.auth import limpiar_nombre, validar_nombre

MAXIMO_EN_LOTE = 100


class CambioRolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: Literal["estudiante", "docente", "admin"]


class PerfilEditarIn(BaseModel):
    """PATCH /me (HU-B-407): solo nombre y apellido. Cualquier otro campo (rol, nivel...)
    es un 400: `extra="forbid"`."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(
        default=None, min_length=NOMBRE_PERSONA_MIN, max_length=NOMBRE_PERSONA_MAX
    )
    apellido: str | None = Field(
        default=None, min_length=APELLIDO_PERSONA_MIN, max_length=APELLIDO_PERSONA_MAX
    )

    _limpiar = field_validator("nombre", "apellido", mode="before")(limpiar_nombre)
    _validar = field_validator("nombre", "apellido")(validar_nombre)

    @model_validator(mode="after")
    def exigir_algun_campo(self) -> Self:
        if self.nombre is None and self.apellido is None:
            raise ValueError("Envía el nombre, el apellido o ambos.")
        return self

    def cambios(self) -> dict[str, str]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class PermisoNombreIn(BaseModel):
    """Permiso para que una persona edite su nombre y apellido (lo da un administrador)."""

    model_config = ConfigDict(extra="forbid")

    puede_editar_nombre: StrictBool


class PermisoNombreEnLoteIn(PermisoNombreIn):
    usuario_ids: list[UUID] = Field(min_length=1, max_length=MAXIMO_EN_LOTE)

    @field_validator("usuario_ids")
    @classmethod
    def sin_repetidos(cls, ids: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(ids))
