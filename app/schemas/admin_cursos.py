from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ACTIVIDAD_DIAS_DEFECTO,
    ACTIVIDAD_DIAS_MAX,
    ACTIVIDAD_DIAS_MIN,
)
from app.core.longitudes import POR_PAGINA_MAX
from app.schemas.contenido import Busqueda
from app.schemas.curso import CursoCreate


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
    # Solo los cursos disponibles, sin docente (HU-B-418: cifra del panel de docentes).
    sin_docente: bool = False
    estado: Literal["activo", "archivado"] | None = None
    q: Busqueda | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class ReasignarCursoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docente_id: UUID


class CursoAdminCrear(CursoCreate):
    """POST /admin/cursos (HU-B-413): como crear un curso, y opcionalmente con docente.
    Sin docente queda disponible hasta que el admin le asigne uno (HU-B-417)."""

    docente_id: UUID | None = None


class FiltrosActividadDocentes(BaseModel):
    """Query string de GET /admin/docentes/actividad (HU-B-418)."""

    model_config = ConfigDict(extra="forbid")

    estado_actividad: Literal["activo", "inactivo", "sin_actividad"] | None = None
    q: Busqueda | None = None
    orden: Literal["ultima_actividad", "-acciones_30d", "-cursos", "-estudiantes", "nombre"] = (
        "nombre"
    )
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)


class ResumenActividadQuery(BaseModel):
    """Query string de GET /admin/docentes/{id}/actividad/resumen."""

    model_config = ConfigDict(extra="forbid")

    dias: int = Field(default=ACTIVIDAD_DIAS_DEFECTO, ge=ACTIVIDAD_DIAS_MIN, le=ACTIVIDAD_DIAS_MAX)


class LineaDeTiempoQuery(BaseModel):
    """Query string de GET /admin/docentes/{id}/actividad."""

    model_config = ConfigDict(extra="forbid")

    tipo: (
        Literal[
            "sesion",
            "leccion",
            "ejercicio",
            "evaluacion",
            "retroalimentacion",
            "mensaje",
            "curso",
            "contenido",
        ]
        | None
    ) = None
    curso_id: int | None = Field(default=None, ge=1)
    desde: date | None = None
    hasta: date | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)
