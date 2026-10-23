# =========================================================
# Configuracion unica de la aplicacion, leida del entorno
# (.env en local). Si falta una variable o tiene un valor peligroso,
# la app no arranca y el error nombra la variable (nunca su valor).
# Guia de valores: docs/configuracion-entornos.md
# =========================================================
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

ENTORNO_PRODUCCION = "production"
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Valores cerrados: un error de escritura ("produccion") no puede desactivar
    # en silencio las protecciones de produccion (HU-B-316, R1).
    app_env: Literal["local", "staging", "production"] = "local"
    flask_debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    # Proyecto de Supabase: de aqui salen el emisor y las claves publicas (JWKS)
    # con que se validan los tokens de los usuarios.
    supabase_url: str
    # UNICA conexion a PostgreSQL: Session pooler de Supabase (puerto 5432).
    # La usan la app y Alembic. Contiene la contrasena: es secreta (HU-B-315).
    database_url: SecretStr
    # Clave secreta service_role de Supabase (SOLO servidor): registro de estudiantes e
    # invitacion de docentes (HU-B-318). Opcional: sin ella esos endpoints responden 503.
    supabase_service_role_key: SecretStr | None = None
    # URL publica del frontend: a donde vuelve el usuario desde los correos de
    # confirmacion e invitacion (debe estar en Supabase > Auth > URL Configuration).
    frontend_url: str | None = None
    sqlalchemy_echo: bool = False

    @field_validator("app_env", "log_level", mode="before")
    @classmethod
    def normalizar_mayusculas(cls, valor: object, info) -> object:
        if not isinstance(valor, str):
            return valor
        valor = valor.strip()
        return valor.upper() if info.field_name == "log_level" else valor.lower()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def separar_origenes(cls, valor: object) -> object:
        """CORS_ORIGINS llega como texto separado por comas; sin "/" final."""
        if isinstance(valor, str):
            valor = valor.split(",")
        if isinstance(valor, list):
            return [str(origen).strip().rstrip("/") for origen in valor if str(origen).strip()]
        return valor

    @field_validator("cors_origins")
    @classmethod
    def exigir_origenes_explicitos(cls, origenes: list[str]) -> list[str]:
        # R4: "*" permitiria que cualquier sitio web use la API desde el navegador.
        for origen in origenes:
            if "*" in origen:
                raise ValueError("no se permite '*': lista los origenes exactos del frontend")
            if not origen.startswith(("http://", "https://")):
                raise ValueError("cada origen debe empezar por http:// o https://")
        return origenes

    @model_validator(mode="after")
    def prohibir_depuracion_en_produccion(self) -> Self:
        # R3: el depurador de Flask ejecuta codigo desde el navegador y SQLALCHEMY_ECHO
        # escribe datos de estudiantes en los logs.
        if self.es_produccion and self.flask_debug:
            raise ValueError("FLASK_DEBUG debe ser 0 cuando APP_ENV=production")
        if self.es_produccion and self.sqlalchemy_echo:
            raise ValueError("SQLALCHEMY_ECHO debe ser 0 cuando APP_ENV=production")
        return self

    def url_base_de_datos(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def es_produccion(self) -> bool:
        return self.app_env == ENTORNO_PRODUCCION

    @property
    def base_es_local(self) -> bool:
        return make_url(self.url_base_de_datos()).host in HOSTS_LOCALES

    @property
    def emisor_jwt(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        """Claves publicas del proyecto (ES256); no es un secreto."""
        return f"{self.emisor_jwt}/.well-known/jwks.json"

    def motivo_para_bloquear_operacion(self, *, confirmado: bool) -> str | None:
        """Para herramientas que modifican la base (Alembic, scripts). None = se puede."""
        if self.app_env == "local" and not self.base_es_local:
            # R2: el .env dice "local" pero la base es remota (posiblemente produccion).
            return (
                "APP_ENV=local pero DATABASE_URL apunta a una base remota. Si es la base de "
                "produccion usa APP_ENV=production; si es una base de pruebas, APP_ENV=staging."
            )
        if self.es_produccion and not confirmado:
            return "APP_ENV=production: esta operacion requiere confirmacion explicita."
        return None


class ConfiguracionInvalida(RuntimeError):
    """Variables de entorno faltantes o invalidas. Nunca incluye sus valores."""


def _describir(error: dict) -> str:
    # Pydantic no incluye el valor recibido en "msg": se puede mostrar sin filtrar secretos.
    variable = str(error["loc"][0]).upper() if error["loc"] else ""
    if error["type"] == "literal_error":
        mensaje = "debe ser uno de: " + error["ctx"]["expected"].replace(" or ", " o ")
    else:
        mensaje = error["msg"].removeprefix("Value error, ")
    return f"{variable}: {mensaje}" if variable else mensaje


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        problemas = sorted(_describir(e) for e in error.errors())
        raise ConfiguracionInvalida(
            "Configuracion invalida. Revisa estas variables de entorno: " + "; ".join(problemas)
        ) from None
