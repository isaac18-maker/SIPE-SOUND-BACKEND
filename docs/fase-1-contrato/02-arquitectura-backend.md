# 02 · Arquitectura y estructura de carpetas (Backend)

## 1. Stack

| Pieza | Tecnología | Nota |
|---|---|---|
| Lenguaje | Python ≥ 3.11 | `pyproject.toml` + `uv` como gestor. |
| Framework HTTP | Flask 3 | App factory + Blueprints. |
| Validación / DTO | Pydantic v2 | Entrada y salida de la API. |
| ORM | SQLAlchemy 2.x (estilo 2.0, tipado) | Desde Fase 3. En Fase 2 se sigue usando el cliente de Supabase detrás de repositorios. |
| Migraciones | Alembic | Carpeta `migrations/versions/`. |
| Base de datos | PostgreSQL gestionado por Supabase | Supabase Auth sigue siendo el proveedor de identidad. |
| Autenticación | JWT emitido por Supabase Auth | El backend valida el token; el frontend nunca consulta tablas directamente. |
| Calidad | Ruff (lint + format) + SonarQube | Sin cobertura obligatoria en esta etapa. |

## 2. Estructura objetivo

```
SIPE-SOUND-BACKEND/
├── AGENTS.md                     # punto de entrada para agentes de IA
├── CLAUDE.md                     # importa AGENTS.md
├── alembic.ini
├── pyproject.toml
├── sonar-project.properties
├── run.py                        # arranque local (lee FLASK_DEBUG del entorno)
├── wsgi.py                       # arranque en servidor (gunicorn/waitress)
├── .env.example
├── docs/                         # este directorio
├── migrations/
│   ├── env.py                    # con las protecciones del contrato de BD
│   ├── script.py.mako
│   ├── README.md
│   └── versions/                 # una revisión por cambio de esquema
├── scripts/
│   ├── check_migrations.py       # guardia anti-operaciones destructivas
│   └── seed_dev.py               # datos de ejemplo SOLO para local
├── db/
│   └── legacy/
│       └── schema_supabase_v0.sql   # script histórico (solo referencia)
└── app/
    ├── __init__.py               # create_app(): solo ensambla
    ├── container.py              # composition root: servicio + repositorio (fuera de las capas)
    ├── core/                     # transversal, sin lógica de negocio
    │   ├── config.py             # Settings (pydantic-settings) por entorno
    │   ├── errors.py             # jerarquía AppError + handlers
    │   ├── responses.py          # ok(), created(), paginated()
    │   ├── security.py           # auth_required, roles_required, CurrentUser
    │   ├── logging.py
    │   └── constants.py
    ├── api/
    │   └── v1/
    │       ├── __init__.py       # register_v1(app): registra blueprints
    │       ├── health.py
    │       ├── bloques.py
    │       ├── lecciones.py
    │       ├── ejercicios.py
    │       ├── acordes.py
    │       ├── progreso.py
    │       ├── evaluaciones.py
    │       ├── cursos.py         # lado estudiante (unirse, mis cursos)
    │       └── docente/          # /api/v1/docente/...
    │           ├── __init__.py
    │           ├── cursos.py
    │           ├── contenido.py
    │           ├── estudiantes.py
    │           └── evaluaciones.py
    ├── schemas/                  # Pydantic: <Entidad>Create, <Entidad>Update, <Entidad>Out
    ├── services/                 # reglas de negocio, una clase por agregado
    ├── repositories/             # acceso a datos; un repositorio por agregado
    │   ├── base.py               # protocolos (interfaces)
    │   └── sqlalchemy/           # implementaciones concretas (Fase 3)
    ├── models/                   # SQLAlchemy ORM (Fase 3)
    │   ├── base.py               # Base, naming_convention, mixins
    │   └── <entidad>.py
    └── infrastructure/
        ├── database.py           # engine, SessionLocal, session_scope()
        └── supabase_client.py    # cliente Supabase (auth)
```

## 3. Capas y regla de dependencia

```
api (controladores)  →  services  →  repositories  →  models / infrastructure
        ↓                   ↓
     schemas             schemas
        └──────── core (puede usarse desde cualquier capa) ────────┘
```

| Capa | Responsabilidad | Prohibido |
|---|---|---|
| `api/` | Leer la petición, validar con un schema, llamar **un** método de servicio, devolver con `responses.*`. | Consultar BD, contener `if` de negocio, construir SQL, capturar `Exception` genérica. |
| `services/` | Reglas de negocio (aprobación de evaluación, desbloqueo, permisos sobre recursos propios). | Importar `flask.request`, `jsonify`, devolver `Response`. |
| `repositories/` | CRUD y consultas. Devuelven modelos o DTO. | Reglas de negocio, lanzar errores HTTP. |
| `models/` | Mapeo ORM y restricciones. | Lógica, llamadas externas. |
| `core/` | Config, errores, seguridad, respuestas. | Depender de `services` o `api`. |

Una capa **solo** importa de la capa inmediatamente inferior o de `core`/`schemas`.
`ruff` no lo valida; se revisa en el PR.

## 4. SOLID aplicado

| Principio | Cómo se cumple aquí | Ejemplo concreto |
|---|---|---|
| **S** – Responsabilidad única | Controlador = HTTP; servicio = negocio; repositorio = datos. | La calificación del quiz sale del blueprint a `EvaluacionService.calificar()`. |
| **O** – Abierto/cerrado | Nuevos tipos de pregunta se agregan con una nueva estrategia de calificación, sin tocar las existentes. | `CalificadorOpcionUnica`, futuro `CalificadorAudio`. |
| **L** – Sustitución de Liskov | Toda implementación de un repositorio respeta el protocolo y sus excepciones. | `SupabaseLeccionRepository` (Fase 2) y `SqlLeccionRepository` (Fase 3) son intercambiables. |
| **I** – Segregación de interfaces | Protocolos pequeños por necesidad. | `LectorLecciones` vs `EditorLecciones`; el servicio público solo pide el lector. |
| **D** – Inversión de dependencias | Los servicios reciben repositorios por constructor; el ensamblado se hace en un único lugar. | `app/container.py` (*composition root*). No va en `core/` porque depende de `services` y `repositories`. |

### Ejemplo de referencia (forma esperada)

```python
# app/repositories/base.py
from typing import Protocol, Sequence
from app.schemas.leccion import LeccionOut

class LectorLecciones(Protocol):
    def listar(self, *, bloque_id: int | None = None) -> Sequence[LeccionOut]: ...
    def obtener(self, leccion_id: int) -> LeccionOut | None: ...
```

```python
# app/services/leccion_service.py
from app.core.errors import NoEncontrado
from app.repositories.base import LectorLecciones

class LeccionService:
    def __init__(self, lector: LectorLecciones) -> None:
        self._lector = lector

    def obtener(self, leccion_id: int):
        leccion = self._lector.obtener(leccion_id)
        if leccion is None:
            raise NoEncontrado("leccion", leccion_id)
        return leccion
```

```python
# app/api/v1/lecciones.py
from flask import Blueprint
from app.core.responses import ok
from app.container import leccion_service

bp = Blueprint("lecciones", __name__)

@bp.get("/lecciones/<int:leccion_id>")
def obtener_leccion(leccion_id: int):
    return ok(leccion_service().obtener(leccion_id))
```

## 5. Configuración por entorno

- `app/core/config.py` expone `get_settings()` (cacheado) con:
  `APP_ENV` (`local|staging|production`), `DATABASE_URL`, `DATABASE_URL_MIGRATIONS`,
  `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` o `SUPABASE_JWKS_URL`,
  `CORS_ORIGINS` (lista), `FLASK_DEBUG`, `LOG_LEVEL`.
- Si falta una variable obligatoria, la app **no arranca** y dice cuál falta.
- `debug` nunca está fijo en código.

## 6. Decisión sobre RLS y conexión directa

Desde la Fase 3 el backend se conecta a PostgreSQL con SQLAlchemy usando un rol
de servidor. Ese rol **no** está sujeto a RLS, por lo tanto:

1. **Toda autorización vive en `services/`** (ej. "un docente solo ve los cursos donde `docente_id = usuario_actual`").
2. Las políticas RLS se **mantienen** como defensa en profundidad para cualquier acceso con la `anon key`.
3. El frontend solo usa Supabase para **autenticación**; jamás `supabase.from(...)`.
