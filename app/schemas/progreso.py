# =========================================================
# Entrada de los endpoints de progreso.
# =========================================================
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ACTIVIDAD_DIAS_DEFECTO,
    ACTIVIDAD_DIAS_MAX,
    ACTIVIDAD_DIAS_MIN,
    PORCENTAJE_MAXIMO,
    PORCENTAJE_MINIMO,
)
from app.core.longitudes import BPM_MAXIMO, BPM_MINIMO


class AvanceIn(BaseModel):
    """PUT /progreso/lecciones/{id}."""

    model_config = ConfigDict(extra="forbid", strict=True)

    porcentaje: int = Field(default=0, ge=PORCENTAJE_MINIMO, le=PORCENTAJE_MAXIMO)
    completado: bool = False


class AvanceEjercicioIn(AvanceIn):
    """PUT /progreso/ejercicios/{id}: ademas, el tempo al que se logro tocar."""

    mejor_bpm: int | None = Field(default=None, ge=BPM_MINIMO, le=BPM_MAXIMO)


class ActividadQuery(BaseModel):
    """GET /progreso/actividad?dias= (HU-B-324). Llega como texto en la URL: sin strict."""

    model_config = ConfigDict(extra="forbid")

    dias: int = Field(default=ACTIVIDAD_DIAS_DEFECTO, ge=ACTIVIDAD_DIAS_MIN, le=ACTIVIDAD_DIAS_MAX)
