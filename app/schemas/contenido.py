# =========================================================
# Entrada del panel docente: lecciones, ejercicios y bloques (HU-B-309).
# Limites de 04-contrato-api seccion 7 (app/core/longitudes.py); la base
# aplica los mismos con CHECK (0013). Los titulos no aceptan HTML.
# =========================================================
import re
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.core.errors import ValidacionError
from app.core.longitudes import (
    BPM_MAXIMO,
    BPM_MINIMO,
    BUSQUEDA_MAX,
    CONTENIDO_LECCION_MAX,
    DESCRIPCION_MAX,
    DURACION_MIN_MAXIMO,
    DURACION_MIN_MINIMO,
    MAXIMO_ACORDES,
    MAXIMO_PASOS,
    MAXIMO_TEMAS,
    NOMBRE_ACORDE_MAX,
    PASO_MAX,
    PATRON_COMPAS,
    POR_PAGINA_MAX,
    TEMA_MAX,
    TITULO_MAX,
    TITULO_MIN,
)
from app.schemas.video import ConVideo, columnas_de_video

Nivel = Literal["principiante", "intermedio", "avanzado"]
EstadoContenido = Literal["borrador", "publicado", "archivado"]
COMPAS = re.compile(PATRON_COMPAS)


def _sin_html(valor: str) -> str:
    if "<" in valor or ">" in valor:
        raise PydanticCustomError("valor_invalido", "No se permiten los caracteres < ni >.")
    return valor


def _sin_repetidos(valores: list[str]) -> list[str]:
    if len({v.lower() for v in valores}) != len(valores):
        raise PydanticCustomError("valor_invalido", "Hay elementos repetidos.")
    return valores


Titulo = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=TITULO_MIN, max_length=TITULO_MAX),
    AfterValidator(_sin_html),
]
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, max_length=DESCRIPCION_MAX)]


def _items(maximo_largo: int, maximo: int):
    item = Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=maximo_largo)
    ]
    return Annotated[list[item], Field(max_length=maximo), AfterValidator(_sin_repetidos)]


Acordes = _items(NOMBRE_ACORDE_MAX, MAXIMO_ACORDES)
Temas = _items(TEMA_MAX, MAXIMO_TEMAS)
Paso = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=PASO_MAX)]
Pasos = Annotated[list[Paso], Field(max_length=MAXIMO_PASOS)]
Busqueda = Annotated[str, StringConstraints(strip_whitespace=True, max_length=BUSQUEDA_MAX)]
DuracionMin = Annotated[int, Field(ge=DURACION_MIN_MINIMO, le=DURACION_MIN_MAXIMO)]
Bpm = Annotated[int, Field(ge=BPM_MINIMO, le=BPM_MAXIMO)]


class EntradaEditable(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)

    # Campos que la base no admite nulos: en un PATCH no se pueden "borrar".
    NO_NULOS: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="before")
    @classmethod
    def rechazar_nulos(cls, datos: Any) -> Any:
        if isinstance(datos, dict):
            for campo in cls.NO_NULOS:
                if campo in datos and datos[campo] is None:
                    raise PydanticCustomError("valor_invalido", f"{campo}: No puede ser nulo.")
        return datos

    def nuevos(self) -> dict[str, Any]:
        """Los valores para crear la fila (video_url ya traducido a las columnas de video)."""
        return columnas_de_video(self.model_dump())

    def cambios(self) -> dict[str, Any]:
        """Solo lo que se envio; una descripcion vacia se guarda como nula."""
        datos = self.model_dump(exclude_unset=True)
        if not datos:
            raise ValidacionError("Envía al menos un campo para editar.")
        datos = columnas_de_video(datos)
        return {k: (None if v == "" else v) for k, v in datos.items()}


class _Compas(BaseModel):
    @field_validator("compas", check_fields=False)
    @classmethod
    def validar_compas(cls, valor: str | None) -> str | None:
        if valor is not None and not COMPAS.fullmatch(valor):
            raise PydanticCustomError("valor_invalido", "Usa un compás como 4/4, 3/4 o 6/8.")
        return valor


class LeccionCrear(EntradaEditable, ConVideo):
    bloque_id: int = Field(gt=0)
    numero: int = Field(ge=1, le=9999)
    titulo: Titulo
    descripcion: Descripcion | None = None
    contenido: Annotated[str, Field(max_length=CONTENIDO_LECCION_MAX)] | None = None
    nivel: Nivel = "principiante"
    duracion_min: DuracionMin | None = None
    acordes: Acordes = []
    temas: Temas = []


class LeccionEditar(EntradaEditable, ConVideo):
    NO_NULOS = ("bloque_id", "numero", "titulo", "nivel")

    bloque_id: int | None = Field(default=None, gt=0)
    numero: int | None = Field(default=None, ge=1, le=9999)
    titulo: Titulo | None = None
    descripcion: Descripcion | None = None
    contenido: Annotated[str, Field(max_length=CONTENIDO_LECCION_MAX)] | None = None
    nivel: Nivel | None = None
    duracion_min: DuracionMin | None = None
    acordes: Acordes | None = None
    temas: Temas | None = None


class EjercicioCrear(EntradaEditable, _Compas, ConVideo):
    leccion_id: int | None = Field(default=None, gt=0)
    nombre: Titulo
    descripcion: Descripcion | None = None
    nivel: Nivel = "principiante"
    bpm_recomendado: Bpm = 60
    compas: str = "4/4"
    duracion_min: DuracionMin | None = None
    acordes: Acordes = []
    pasos: Pasos = []


class EjercicioEditar(EntradaEditable, _Compas, ConVideo):
    NO_NULOS = ("nombre", "nivel", "bpm_recomendado", "compas")

    leccion_id: int | None = Field(default=None, gt=0)
    nombre: Titulo | None = None
    descripcion: Descripcion | None = None
    nivel: Nivel | None = None
    bpm_recomendado: Bpm | None = None
    compas: str | None = None
    duracion_min: DuracionMin | None = None
    acordes: Acordes | None = None
    pasos: Pasos | None = None


class BloqueCrear(EntradaEditable, ConVideo):
    numero: int = Field(ge=1, le=999)
    titulo: Titulo
    descripcion: Descripcion | None = None
    nivel: Nivel = "principiante"
    orden_index: int = Field(ge=1, le=999)


class BloqueEditar(EntradaEditable, ConVideo):
    NO_NULOS = ("numero", "titulo", "nivel", "orden_index")

    numero: int | None = Field(default=None, ge=1, le=999)
    titulo: Titulo | None = None
    descripcion: Descripcion | None = None
    nivel: Nivel | None = None
    orden_index: int | None = Field(default=None, ge=1, le=999)


class EstadoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: EstadoContenido


class FiltrosContenido(BaseModel):
    """Query string del listado: ?estado=&bloque_id=&leccion_id=&q=&pagina=&por_pagina=."""

    model_config = ConfigDict(extra="forbid")

    estado: EstadoContenido | None = None
    bloque_id: int | None = Field(default=None, gt=0)
    leccion_id: int | None = Field(default=None, gt=0)
    q: Busqueda | None = None
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=POR_PAGINA_MAX)
