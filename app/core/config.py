# =========================================================
# Configuracion unica de la aplicacion, leida del entorno
# (.env en local). Si falta una variable obligatoria, la app
# no arranca y el error nombra la variable.
# =========================================================
from functools import lru_cache
from typing import Annotated

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    flask_debug: bool = False
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    supabase_url: str
    # TODO(HU-B-205): retirar el alias SUPABASE_KEY cuando todos los .env usen SUPABASE_ANON_KEY
    supabase_anon_key: str = Field(
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_KEY")
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def separar_origenes(cls, valor: object) -> object:
        """CORS_ORIGINS llega como texto separado por comas."""
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor


class ConfiguracionInvalida(RuntimeError):
    """Variables de entorno faltantes o invalidas. Nunca incluye sus valores."""


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        # El mensaje de Pydantic copia el entorno completo (secretos incluidos):
        # solo se reportan los nombres de las variables.
        campos = sorted({str(e["loc"][0]).upper() for e in error.errors()})
        raise ConfiguracionInvalida(
            "Faltan o son invalidas estas variables de entorno: " + ", ".join(campos)
        ) from None
