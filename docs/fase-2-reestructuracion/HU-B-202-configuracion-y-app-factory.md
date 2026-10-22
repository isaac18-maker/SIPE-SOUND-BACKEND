# HU-B-202 · Centralizar la configuración por entorno y limpiar la app factory

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 3 puntos |
| Depende de | HU-B-201 |
| Rama | `hu/HU-B-202-config-app-factory` |

## Historia
**Como** desarrollador
**quiero** una única fuente de configuración validada al arrancar
**para** que la app falle rápido y con un mensaje claro si falta una variable, y no exista `debug=True` en producción.

## Contexto
- [app/extensions.py](../../app/extensions.py) lee `os.environ` y crea el cliente de Supabase al importar el módulo (efecto secundario global).
- [run.py](../../run.py) fija `debug=True` (Sonar S4507).
- [app/__init__.py](../../app/__init__.py) usa `CORS(app)` abierto a cualquier origen (Sonar S5122).

## Alcance
**Incluye**
- `app/core/config.py` con `Settings` (pydantic-settings) y `get_settings()` cacheado.
- `app/infrastructure/supabase_client.py` con `get_supabase()` perezoso.
- `run.py` y nuevo `wsgi.py` leyendo configuración.
- CORS restringido a `CORS_ORIGINS`.

**No incluye**
- Mover blueprints (HU-B-203). Los imports de `extensions` se mantienen funcionando mediante un *shim* temporal.

## Prompt de ejecución
```text
Ejecuta HU-B-202 en SIPE-SOUND-BACKEND. Sin cambios funcionales en endpoints.
- Instala pydantic-settings (uv add pydantic-settings).
- Crea app/core/__init__.py y app/core/config.py con una clase Settings que
  lea: APP_ENV, FLASK_DEBUG, LOG_LEVEL, CORS_ORIGINS (lista separada por comas),
  SUPABASE_URL, SUPABASE_ANON_KEY. Acepta SUPABASE_KEY como alias temporal
  de SUPABASE_ANON_KEY. get_settings() con functools.lru_cache.
- Crea app/infrastructure/supabase_client.py con get_supabase() (lru_cache).
- Convierte app/extensions.py en un shim que reexporta lo anterior con un
  comentario "# TODO(HU-B-203): eliminar shim". Ningún import existente se rompe.
- create_app(settings: Settings | None = None): usa CORS(app, origins=...).
- run.py: app.run(debug=settings.flask_debug, port=5000). Crea wsgi.py.
Valida que todos los endpoints respondan igual que antes.
```

## Pasos
1. `uv add pydantic-settings`.
2. Crear `app/core/config.py`:
   ```python
   from functools import lru_cache
   from pydantic import AliasChoices, Field
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class Settings(BaseSettings):
       model_config = SettingsConfigDict(env_file=".env", extra="ignore")

       app_env: str = "local"
       flask_debug: bool = False
       log_level: str = "INFO"
       cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
       supabase_url: str
       supabase_anon_key: str = Field(
           validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_KEY")
       )

   @lru_cache
   def get_settings() -> Settings:
       return Settings()
   ```
   > Para `CORS_ORIGINS` separado por comas, agregar un `field_validator(mode="before")` que haga `split(",")`.
3. Crear `app/infrastructure/supabase_client.py` con `get_supabase()`.
4. Reescribir `app/extensions.py` como shim (exporta `supabase`, `SUPABASE_URL`, `SUPABASE_KEY` desde lo nuevo).
5. Ajustar `create_app` y `run.py`; crear `wsgi.py` (`app = create_app()`).
6. Arrancar sin `.env` (renombrándolo temporalmente) y confirmar el error legible.

## Criterios de aceptación
```gherkin
Escenario: Falta una variable obligatoria
  Dado que SUPABASE_URL no está definida
  Cuando arranco la aplicación
  Entonces el proceso termina con un error que nombra "supabase_url"

Escenario: Debug controlado por entorno
  Dado FLASK_DEBUG=0
  Cuando ejecuto "uv run python run.py"
  Entonces Flask no arranca en modo debug

Escenario: CORS restringido
  Dado CORS_ORIGINS=http://localhost:5173
  Cuando una petición llega con Origin http://malicioso.test
  Entonces la respuesta no incluye Access-Control-Allow-Origin
```

## Verificación manual
```bash
uv run python run.py
curl -i http://localhost:5000/api/health
curl -i -H "Origin: http://malicioso.test" http://localhost:5000/api/health   # sin cabecera ACAO
curl -s http://localhost:5000/api/lecciones | head -c 200                    # igual que antes
```

## Definición de hecho específica
- [ ] `grep -rn "os.environ" app/` solo aparece en `core/config.py` (o en ningún lado).
- [ ] `grep -rn "debug=True" .` sin resultados.
