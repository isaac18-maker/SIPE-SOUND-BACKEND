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
LARGO_MINIMO_SECRETO = 32


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
    # Clave publica (anon / publishable) del proyecto. El backend la usa para hablar con
    # Supabase Auth en nombre del frontend: registro, inicio y cierre de sesion (HU-B-322).
    # No ignora RLS (no es service_role), pero solo vive en el servidor. Sin ella, /auth/* -> 503.
    supabase_anon_key: SecretStr | None = None
    # Cookie httpOnly con el refresh token (HU-B-322). Secure: si no se define, se exige
    # fuera de "local". SameSite "None" solo si frontend y API estan en sitios distintos.
    auth_cookie_secure: bool | None = None
    auth_cookie_samesite: Literal["Lax", "Strict", "None"] = "Lax"
    # UNICA conexion a PostgreSQL: Session pooler de Supabase (puerto 5432).
    # La usan la app y Alembic. Contiene la contrasena: es secreta (HU-B-315).
    database_url: SecretStr
    sqlalchemy_echo: bool = False
    # Clave del HMAC con que se guardan los codigos de verificacion (HU-B-402). Solo se
    # guarda el hash: robar la tabla no basta para usar un codigo. Secreta, 32+ caracteres.
    codigos_secreto: SecretStr
    # Correo saliente (HU-B-401). Sin CORREO_MODO: "archivo" en local y "smtp" fuera de local.
    correo_modo: Literal["smtp", "archivo"] | None = None
    smtp_host: str = "smtp.gmail.com"
    smtp_puerto: int = Field(default=587, ge=1, le=65535)
    smtp_usuario: str | None = None
    # Contrasena de aplicacion de Gmail (16 caracteres). Es secreta.
    smtp_clave_aplicacion: SecretStr | None = None
    correo_remitente: str | None = None
    correo_nombre_remitente: str = "SIPE-SOUND"
    # Origen del frontend para los enlaces de los correos; debe estar en CORS_ORIGINS.
    url_frontend: str | None = None

    @field_validator("auth_cookie_secure", mode="before")
    @classmethod
    def vacio_es_automatico(cls, valor: object) -> object:
        """AUTH_COOKIE_SECURE= (vacio) deja la decision a APP_ENV."""
        return None if isinstance(valor, str) and not valor.strip() else valor

    @field_validator(
        "correo_modo",
        "smtp_usuario",
        "smtp_clave_aplicacion",
        "correo_remitente",
        "url_frontend",
        mode="before",
    )
    @classmethod
    def vacio_es_ausente(cls, valor: object) -> object:
        """Una variable del .env sin valor (SMTP_USUARIO=) cuenta como no definida."""
        if isinstance(valor, str):
            return valor.strip() or None
        return valor

    @field_validator("codigos_secreto")
    @classmethod
    def exigir_secreto_largo(cls, valor: SecretStr) -> SecretStr:
        if len(valor.get_secret_value()) < LARGO_MINIMO_SECRETO:
            raise ValueError(f"debe tener al menos {LARGO_MINIMO_SECRETO} caracteres")
        return valor

    @field_validator("auth_cookie_samesite", mode="before")
    @classmethod
    def capitalizar_samesite(cls, valor: object) -> object:
        return valor.strip().capitalize() if isinstance(valor, str) else valor

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
        # Una cookie de sesion sin Secure viaja en claro por HTTP (HU-B-322).
        if self.app_env != "local" and self.auth_cookie_secure is False:
            raise ValueError("AUTH_COOKIE_SECURE debe ser 1 fuera de APP_ENV=local")
        if self.auth_cookie_samesite == "None" and not self.cookie_segura:
            raise ValueError("AUTH_COOKIE_SAMESITE=None exige AUTH_COOKIE_SECURE=1")
        self._validar_correo()
        return self

    def _validar_correo(self) -> None:
        # Un correo escrito en un archivo nunca debe reemplazar al real fuera de local.
        if self.correo_modo == "archivo" and self.app_env != "local":
            raise ValueError("CORREO_MODO=archivo solo se permite con APP_ENV=local")
        if self.modo_correo == "smtp":
            faltan = [
                nombre
                for nombre, valor in (
                    ("SMTP_HOST", self.smtp_host),
                    ("SMTP_USUARIO", self.smtp_usuario),
                    ("SMTP_CLAVE_APLICACION", self.smtp_clave_aplicacion),
                    ("CORREO_REMITENTE", self.remitente_correo),
                )
                if not valor
            ]
            if faltan:
                raise ValueError("CORREO_MODO=smtp exige " + ", ".join(faltan))
        if self.url_frontend is not None:
            if self.url_frontend.endswith("/"):
                raise ValueError("URL_FRONTEND no debe terminar en '/'")
            if self.url_frontend not in self.cors_origins:
                raise ValueError("URL_FRONTEND debe estar en CORS_ORIGINS")

    def url_base_de_datos(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def es_produccion(self) -> bool:
        return self.app_env == ENTORNO_PRODUCCION

    @property
    def base_es_local(self) -> bool:
        return make_url(self.url_base_de_datos()).host in HOSTS_LOCALES

    @property
    def cookie_segura(self) -> bool:
        if self.auth_cookie_secure is None:
            return self.app_env != "local"
        return self.auth_cookie_secure

    @property
    def modo_correo(self) -> Literal["smtp", "archivo"]:
        if self.correo_modo is not None:
            return self.correo_modo
        return "archivo" if self.app_env == "local" else "smtp"

    @property
    def origen_frontend(self) -> str:
        """Base de los enlaces de los correos: URL_FRONTEND o, sin ella, el primer origen CORS."""
        return self.url_frontend or self.cors_origins[0]

    @property
    def remitente_correo(self) -> str | None:
        return self.correo_remitente or self.smtp_usuario

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
