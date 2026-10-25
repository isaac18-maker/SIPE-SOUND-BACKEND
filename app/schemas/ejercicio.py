from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EjerciciosQuery(BaseModel):
    """GET /ejercicios (HU-B-501): filtro por estado de avance (solo con sesion) y por leccion."""

    # Ruta publica: un parametro desconocido no la rompe (igual que /ruta).
    model_config = ConfigDict(extra="ignore")

    estado: Literal["sin_iniciar", "en_curso", "finalizado"] | None = None
    leccion_id: int | None = Field(default=None, gt=0)
