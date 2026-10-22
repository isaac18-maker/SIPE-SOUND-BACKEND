# 03 · Estándares de código (Backend · Python)

## 1. Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Módulos y paquetes | `snake_case` | `leccion_service.py` |
| Clases | `PascalCase` | `EvaluacionService`, `LeccionOut` |
| Funciones, variables | `snake_case` | `calcular_porcentaje()` |
| Constantes | `UPPER_SNAKE_CASE` | `PORCENTAJE_APROBACION_POR_DEFECTO` |
| Tablas y columnas | `snake_case`, plural en tablas | `intentos_evaluacion.estudiante_id` |
| Endpoints | sustantivos en plural, `kebab-case` | `/api/v1/docente/cursos/{id}/estudiantes` |

- **Dominio en español** (coherente con lo existente: `leccion`, `ejercicio`, `bloque`), **sin tildes ni ñ** en identificadores (`contrasena` no; usar `password`).
- Sufijos técnicos en inglés aceptados: `Service`, `Repository`, `Out`, `Create`, `Update`.
- Booleanos con prefijo: `es_`, `tiene_`, `puede_` (`es_publicado`, `puede_editar`).

## 2. Estilo y herramientas

- **Ruff** como linter y formateador. Configuración mínima en `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RET", "ARG", "PL", "S", "C90", "ERA"]
ignore = ["PLR0913"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.per-file-ignores]
"migrations/versions/*" = ["E501", "N999"]
```

- Tipado en **todas** las firmas públicas (`def listar(self, bloque_id: int | None) -> list[LeccionOut]`).
- Imports absolutos (`from app.core.errors import NoEncontrado`), nunca relativos de más de un nivel.
- Docstring de una línea en servicios públicos que explique *la regla*, no el *cómo*.

## 3. Reglas alineadas con SonarQube

| Regla Sonar | Qué exige | Cómo se aplica aquí |
|---|---|---|
| S3776 Complejidad cognitiva | ≤ 15 por función | Extraer funciones privadas; usar *early return*. Objetivo interno: ≤ 10. |
| S1192 Literales duplicados | Un literal no se repite ≥ 3 veces | Constantes en `core/constants.py` o `Enum`. |
| S2068 / S6418 Credenciales en código | Ningún secreto en el repo | Todo por `get_settings()`. |
| S4507 Debug en producción | `debug=True` prohibido en código | `run.py` lee `FLASK_DEBUG`. |
| S5122 CORS permisivo | No `CORS(app)` abierto | `CORS(app, origins=settings.cors_origins)`. |
| S1481 / S1854 Variables sin uso / asignaciones muertas | Prohibido | Ruff `F841`. |
| S125 Código comentado | Prohibido | Ruff `ERA001`. |
| S112 / S5754 Excepciones genéricas | No `except Exception:` silencioso | Capturar la excepción concreta y relanzar como `AppError`. |
| S107 Demasiados parámetros | ≤ 7 | Agrupar en un schema Pydantic. |
| S3516 / S1871 Ramas idénticas | Prohibido | Revisión en PR. |

**Quality Gate del proyecto (fases 1–3):** 0 bugs nuevos, 0 vulnerabilidades nuevas,
0 *security hotspots* sin revisar, duplicación en código nuevo ≤ 3 %,
*maintainability rating* A. **La condición de cobertura está desactivada** hasta
que el equipo habilite pruebas.

## 4. Errores

Jerarquía única en `app/core/errors.py`:

```python
class AppError(Exception):
    status = 500
    code = "ERROR_INTERNO"

class ValidacionError(AppError):    status, code = 400, "VALIDACION"
class NoAutenticado(AppError):      status, code = 401, "NO_AUTENTICADO"
class SinPermiso(AppError):         status, code = 403, "SIN_PERMISO"
class NoEncontrado(AppError):       status, code = 404, "NO_ENCONTRADO"
class Conflicto(AppError):          status, code = 409, "CONFLICTO"
```

- Los servicios **lanzan** estas excepciones; un `errorhandler` registrado en `create_app` las convierte al formato del [contrato de API](04-contrato-api.md#3-errores).
- Nunca se devuelve `resp.text` de Supabase/PostgreSQL al cliente: se registra en el log y se responde un mensaje genérico.

## 5. Logging

- `logging.getLogger(__name__)` por módulo; nada de `print`.
- Nunca se registran tokens, contraseñas ni cuerpos completos de petición.
- Nivel por `LOG_LEVEL`.

## 6. Validación de entrada

- Todo `request.get_json()` pasa por un schema Pydantic (`LeccionCreate.model_validate(...)`).
- Los `ValidationError` de Pydantic se transforman en `ValidacionError` con `details` por campo.
- Los *path params* se tipan en la ruta (`<int:leccion_id>`).

## 7. Transacciones (Fase 3)

- Una petición = una unidad de trabajo: `with session_scope() as session:` en el servicio o en un decorador.
- Los repositorios **no** hacen `commit()`; lo hace la unidad de trabajo.

## 8. Lo que NO se hace

- Lógica en `__init__.py` más allá del ensamblado.
- Variables globales mutables (excepto el engine/cliente creados una vez en `infrastructure`).
- `from x import *`.
- Respuestas con formas distintas para el mismo recurso.
- Pruebas unitarias (decisión temporal del equipo, ver contrato de IA R8).
