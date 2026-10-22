from typing import Literal

from pydantic import BaseModel, ConfigDict


class CambioRolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: Literal["estudiante", "docente", "admin"]
