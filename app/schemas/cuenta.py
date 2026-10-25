from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.longitudes import EMAIL_MAX, PASSWORD_MAX, PASSWORD_MIN
from app.schemas.auth import (
    CodigoIn,
    exigir_letras_y_numeros,
    exigir_token,
    limpiar_texto,
    normalizar_email,
)


class ReautenticacionIn(BaseModel):
    """Paso 1 de la verificacion de identidad: la contrasena actual (HU-B-404)."""

    model_config = ConfigDict(extra="forbid")

    # Se envia tal cual a Supabase: no se recorta ni se normaliza.
    password_actual: str = Field(min_length=1, max_length=PASSWORD_MAX)


class ConfirmarReautenticacionIn(CodigoIn):
    """Paso 2: el codigo que llego al correo actual."""


class TokenReautenticacionIn(BaseModel):
    """Base de las operaciones que exigen haber confirmado la identidad."""

    model_config = ConfigDict(extra="forbid")

    token_reautenticacion: str

    _limpiar = field_validator("token_reautenticacion", mode="before")(limpiar_texto)
    _formato = field_validator("token_reautenticacion")(
        exigir_token("Vuelve a confirmar tu identidad.")
    )


class CambiarContrasenaIn(TokenReautenticacionIn):
    password_nueva: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    _password = field_validator("password_nueva")(exigir_letras_y_numeros)


class CambiarCorreoIn(TokenReautenticacionIn):
    email_nuevo: str = Field(max_length=EMAIL_MAX)

    _email = field_validator("email_nuevo", mode="before")(normalizar_email)


class ConfirmarCorreoIn(CodigoIn):
    """El codigo que llego al correo NUEVO."""
