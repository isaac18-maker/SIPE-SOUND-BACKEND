from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.longitudes import (
    APELLIDO_PERSONA_MAX,
    APELLIDO_PERSONA_MIN,
    EMAIL_MAX,
    NOMBRE_PERSONA_MAX,
    NOMBRE_PERSONA_MIN,
    POR_PAGINA_MAX,
)
from app.schemas.auth import PATRON_EMAIL, limpiar_nombre, validar_nombre
from app.schemas.contenido import Busqueda
from app.schemas.perfil import MAXIMO_EN_LOTE

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
    orden: Literal["nombre", "apellido", "rol", "-creado_en", "-ultimo_acceso"] = "nombre"
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class VerificacionManualIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: Motivo | None = None


class CambioEstadoIn(BaseModel):
    """{estado: "suspendida"} o {estado: "activa"}. El motivo es opcional (sin él queda el
    texto por defecto) y `notificar` envía un correo a la persona afectada."""

    model_config = ConfigDict(extra="forbid")

    estado: Literal["activa", "suspendida"]
    motivo: Motivo | None = None
    notificar: StrictBool = False


class EditarCuentaIn(BaseModel):
    """PATCH /admin/usuarios/<id>: nombre, apellido y correo. Los tres son obligatorios."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=NOMBRE_PERSONA_MIN, max_length=NOMBRE_PERSONA_MAX)
    apellido: str = Field(min_length=APELLIDO_PERSONA_MIN, max_length=APELLIDO_PERSONA_MAX)
    email: str = Field(max_length=EMAIL_MAX)

    _limpiar = field_validator("nombre", "apellido", mode="before")(limpiar_nombre)
    _validar = field_validator("nombre", "apellido")(validar_nombre)

    @field_validator("email")
    @classmethod
    def normalizar_correo(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not PATRON_EMAIL.fullmatch(valor):
            raise ValueError("Escribe un correo válido, por ejemplo nombre@correo.com.")
        return valor


class AccionEnLoteIn(BaseModel):
    """POST /admin/usuarios/lote: una acción para varias cuentas."""

    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] = Field(min_length=1, max_length=MAXIMO_EN_LOTE)
    accion: Literal["rol", "activar", "suspender", "reenviar"]
    rol: Rol | None = None
    notificar: StrictBool = False

    @field_validator("ids")
    @classmethod
    def sin_repetidos(cls, ids: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(ids))

    @model_validator(mode="after")
    def exigir_rol(self) -> Self:
        if self.accion == "rol" and self.rol is None:
            raise ValueError("Indica a qué rol pasan las cuentas.")
        return self


class EliminarCuentaIn(BaseModel):
    """El correo de la cuenta, escrito a mano, confirma que no es un clic accidental."""

    model_config = ConfigDict(extra="forbid")

    confirmacion: str = Field(min_length=1, max_length=EMAIL_MAX)

    @field_validator("confirmacion")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        return valor.strip().lower()
