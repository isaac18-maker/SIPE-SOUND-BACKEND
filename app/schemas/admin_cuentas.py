from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.longitudes import EMAIL_MAX, POR_PAGINA_MAX
from app.schemas.contenido import Busqueda

EstadoCuenta = Literal["pendiente_verificacion", "activa", "suspendida"]
Rol = Literal["estudiante", "docente", "admin"]
# El motivo queda en la auditoria: 10 a 300 caracteres, sin espacios en los extremos.
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=300)]


class FiltrosUsuarios(BaseModel):
    """Query string de GET /admin/usuarios."""

    model_config = ConfigDict(extra="forbid")

    rol: Rol | None = None
    estado: EstadoCuenta | None = None
    q: Busqueda | None = None
    puede_editar_nombre: bool | None = None
    orden: Literal["nombre", "-creado_en", "-ultimo_acceso"] = "nombre"
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class VerificacionManualIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: Motivo


class CambioEstadoIn(BaseModel):
    """{estado: "suspendida", motivo} o {estado: "activa"}."""

    model_config = ConfigDict(extra="forbid")

    estado: Literal["activa", "suspendida"]
    motivo: Motivo | None = None

    @model_validator(mode="after")
    def exigir_motivo_al_suspender(self) -> Self:
        if self.estado == "suspendida" and self.motivo is None:
            raise ValueError("Indica el motivo de la suspensión (de 10 a 300 caracteres).")
        if self.estado == "activa":
            self.motivo = None
        return self


class EliminarCuentaIn(BaseModel):
    """El correo de la cuenta, escrito a mano, confirma que no es un clic accidental."""

    model_config = ConfigDict(extra="forbid")

    confirmacion: str = Field(min_length=1, max_length=EMAIL_MAX)

    @field_validator("confirmacion")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return valor.strip().lower()
