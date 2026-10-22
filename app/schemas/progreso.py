# =========================================================
# Entrada de los endpoints de progreso.
# ProgresoCreate (POST /progreso, compatibilidad): los mensajes y el orden
# de las validaciones replican el comportamiento anterior al refactor.
# =========================================================
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from app.core.constants import PORCENTAJE_MAXIMO, PORCENTAJE_MINIMO, TIPO_EJERCICIO, TIPO_LECCION

BPM_MINIMO = 20
BPM_MAXIMO = 300


def _invalido(mensaje: str) -> PydanticCustomError:
    return PydanticCustomError("valor_invalido", mensaje)


class ProgresoCreate(BaseModel):
    tipo: Any = None
    contenido_id: Any = None
    porcentaje: Any = 0
    completado: Any = False

    @field_validator("tipo", mode="before")
    @classmethod
    def validar_tipo(cls, valor: Any) -> str:
        if valor not in (TIPO_LECCION, TIPO_EJERCICIO):
            raise _invalido("El campo 'tipo' debe ser 'leccion' o 'ejercicio'")
        return valor

    @field_validator("contenido_id", mode="before")
    @classmethod
    def validar_contenido_id(cls, valor: Any) -> int:
        if not isinstance(valor, int):
            raise _invalido("El campo 'contenido_id' es obligatorio y debe ser un numero")
        return valor

    @field_validator("porcentaje", mode="before")
    @classmethod
    def validar_porcentaje(cls, valor: Any) -> int:
        if not isinstance(valor, int) or not PORCENTAJE_MINIMO <= valor <= PORCENTAJE_MAXIMO:
            raise _invalido("El campo 'porcentaje' debe ser un numero entre 0 y 100")
        return valor


class AvanceIn(BaseModel):
    """PUT /progreso/lecciones/{id}."""

    model_config = ConfigDict(extra="forbid", strict=True)

    porcentaje: int = Field(default=0, ge=PORCENTAJE_MINIMO, le=PORCENTAJE_MAXIMO)
    completado: bool = False


class AvanceEjercicioIn(AvanceIn):
    """PUT /progreso/ejercicios/{id}: ademas, el tempo al que se logro tocar."""

    mejor_bpm: int | None = Field(default=None, ge=BPM_MINIMO, le=BPM_MAXIMO)
