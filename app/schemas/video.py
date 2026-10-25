# =========================================================
# Video guia de YouTube en bloques, lecciones, ejercicios y acordes (HU-B-410).
# La API recibe `video_url` y guarda solo el id (`video_youtube_id`): nada de la URL original
# se almacena ni se devuelve. `video_inicio_seg`, si viene, gana sobre el t= de la URL.
# =========================================================
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from pydantic_core import PydanticCustomError

from app.core.longitudes import VIDEO_INICIO_MAX, VIDEO_URL_MAX
from app.core.youtube import VideoInvalido, extraer_video


def _es_enlace_de_youtube(valor: str) -> str:
    if not valor:  # "" equivale a null (quitar el video), como en el resto de campos de la API
        return valor
    try:
        extraer_video(valor)
    except VideoInvalido as error:
        raise PydanticCustomError("valor_invalido", str(error)) from None
    return valor


VideoUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=VIDEO_URL_MAX),
    AfterValidator(_es_enlace_de_youtube),
]
InicioSeg = Annotated[int, Field(ge=0, le=VIDEO_INICIO_MAX)]


class ConVideo(BaseModel):
    """Campos de video de las entradas de crear/editar. `video_url: null` quita el video."""

    model_config = ConfigDict(extra="forbid")

    video_url: VideoUrl | None = None
    video_inicio_seg: InicioSeg | None = None


class VideoAcordeIn(BaseModel):
    """PUT /admin/acordes/{id}/video."""

    model_config = ConfigDict(extra="forbid")

    video_url: VideoUrl
    video_inicio_seg: InicioSeg | None = None


def columnas_de_video(datos: dict[str, Any]) -> dict[str, Any]:
    """De los campos de la API (video_url, video_inicio_seg) a las columnas de la base
    (video_youtube_id, video_inicio_seg). No toca nada si el dato no trae video."""
    if "video_url" not in datos and "video_inicio_seg" not in datos:
        return datos
    resultado = {k: v for k, v in datos.items() if k not in {"video_url", "video_inicio_seg"}}
    inicio = datos.get("video_inicio_seg")
    if "video_url" in datos:
        url = datos["video_url"]
        if not url:  # null o "": se quita el video y su segundo de inicio
            resultado.update(video_youtube_id=None, video_inicio_seg=None)
        else:
            video_id, inicio_url = extraer_video(url)
            resultado.update(
                video_youtube_id=video_id,
                video_inicio_seg=inicio if inicio is not None else inicio_url,
            )
    else:  # solo cambia el segundo de inicio de un video que ya existe
        resultado["video_inicio_seg"] = inicio
    return resultado
