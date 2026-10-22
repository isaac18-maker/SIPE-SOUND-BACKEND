# =========================================================
# Configuracion unica de la aplicacion, leida del entorno
# (.env en local). Si falta una variable obligatoria, la app
# no arranca y el error nombra la variable.
# =========================================================
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
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
    supabase_anon_key: str
    # Verificacion del JWT: JWKS para claves asimetricas (ES256/RS256) o
    # secreto compartido para proyectos con la clave HS256 heredada.
    supabase_jwks_url: str | None = None
    supabase_jwt_secret: SecretStr | None = None
    # Acceso a datos: "supabase" (API REST con la anon key) o "sql" (SQLAlchemy).
    # TODO(HU-B-312): retirar "supabase" y la variable cuando todo use SQLAlchemy.
    data_backend: Literal["supabase", "sql"] = "supabase"
    # Conexion de la app (pooler de Supabase, puerto 6543) y conexion directa
    # para migraciones (puerto 5432). Ambas contienen la contrasena: son secretas.
    # DATABASE_URL es obligatoria para la app desde HU-B-304 (el rol se lee siempre
    # con la conexion del servidor). Alembic y los scripts de solo migraciones no la usan.
    database_url: SecretStr | None = None
    database_url_migrations: SecretStr | None = None
    sqlalchemy_echo: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def separar_origenes(cls, valor: object) -> object:
        """CORS_ORIGINS llega como texto separado por comas."""
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor

    @model_validator(mode="after")
    def exigir_verificacion_jwt(self) -> Self:
        if not self.supabase_jwks_url and not self.supabase_jwt_secret:
            raise ValueError("define SUPABASE_JWKS_URL o SUPABASE_JWT_SECRET")
        return self

    def url_base_de_datos(self) -> str:
        """URL de la app; falla con un mensaje claro si no esta configurada."""
        if self.database_url is None:
            raise ConfiguracionInvalida(
                "Configuracion invalida. Revisa estas variables de entorno: DATABASE_URL"
            )
        return self.database_url.get_secret_value()

    @property
    def emisor_jwt(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


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
