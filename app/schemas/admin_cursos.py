from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.longitudes import POR_PAGINA_MAX
from app.schemas.contenido import Busqueda


class FiltrosDocentes(BaseModel):
    """Query string de GET /admin/docentes."""

    model_config = ConfigDict(extra="forbid")

    q: Busqueda | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class FiltrosCursosAdmin(BaseModel):
    """Query string de GET /admin/cursos."""

    model_config = ConfigDict(extra="forbid")

    docente_id: UUID | None = None
    estado: Literal["activo", "archivado"] | None = None
    q: Busqueda | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class ReasignarCursoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docente_id: UUID
