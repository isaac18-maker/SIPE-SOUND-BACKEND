# =========================================================
# Configuracion unica de la aplicacion, leida del entorno
# (.env en local). Si falta una variable obligatoria, la app
# no arranca y el error nombra la variable.
# =========================================================
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    flask_debug: bool = False
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    # Proyecto de Supabase: de aqui salen el emisor y las claves publicas (JWKS)
    # con que se validan los tokens de los usuarios.
    supabase_url: str
    # UNICA conexion a PostgreSQL: Session pooler de Supabase (puerto 5432).
    # La usan la app y Alembic. Contiene la contrasena: es secreta (HU-B-315).
    database_url: SecretStr
    sqlalchemy_echo: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def separar_origenes(cls, valor: object) -> object:
        """CORS_ORIGINS llega como texto separado por comas."""
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor

    def url_base_de_datos(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def emisor_jwt(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        """Claves publicas del proyecto (ES256); no es un secreto."""
        return f"{self.emisor_jwt}/.well-known/jwks.json"


class ConfiguracionInvalida(RuntimeError):
    """Variables de entorno faltantes o invalidas. Nunca incluye sus valores."""


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        # El mensaje de Pydantic copia el entorno completo (secretos incluidos):
        # solo se reportan los nombres de las variables o la regla incumplida.
        problemas = sorted(
            str(e["loc"][0]).upper() if e["loc"] else e["msg"] for e in error.errors()
        )
        raise ConfiguracionInvalida(
            "Configuracion invalida. Revisa estas variables de entorno: " + "; ".join(problemas)
        ) from None
