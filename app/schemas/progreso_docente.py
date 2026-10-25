from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.curso import EstudiantesQuery


class ProgresoQuery(BaseModel):
    """GET /docente/progreso: ?curso_id= (opcional) y, solo para el admin, ?docente_id=."""

    model_config = ConfigDict(extra="forbid")

    curso_id: int | None = Field(default=None, gt=0)
    docente_id: UUID | None = None


class MatrizQuery(EstudiantesQuery):
    """GET /docente/progreso/matriz: el curso es obligatorio; ?q=&orden=&pagina=&por_pagina=."""

    curso_id: int = Field(gt=0)


class DetalleProgresoQuery(BaseModel):
    """GET /docente/progreso/estudiantes/{id}: ?docente_id= solo para el admin."""

    model_config = ConfigDict(extra="forbid")

    docente_id: UUID | None = None
