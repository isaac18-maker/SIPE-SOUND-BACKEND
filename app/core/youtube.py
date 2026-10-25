# =========================================================
# Enlaces de YouTube (HU-B-410). Funcion pura: de una URL saca el id del video (11
# caracteres) y, si trae, el segundo de inicio. Solo acepta dominios de YouTube y NUNCA
# llama a la red. El backend guarda solo el id; la URL original se descarta.
# =========================================================
import re
from urllib.parse import parse_qs, urlsplit

from app.core.longitudes import VIDEO_INICIO_MAX, VIDEO_URL_MAX

MENSAJE_VIDEO = "Pega el enlace de un video de YouTube (por ejemplo, https://youtu.be/…)."

PATRON_ID = re.compile(r"[A-Za-z0-9_-]{11}")
# 90, 90s, 1m30s, 1h2m3s
PATRON_TIEMPO = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
HOSTS_YOUTUBE = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
HOSTS_CORTOS = {"youtu.be", "www.youtu.be"}
HOSTS_SIN_COOKIES = {"youtube-nocookie.com", "www.youtube-nocookie.com"}
# Rutas /<tipo>/<id> que identifican un video.
TIPOS_DE_RUTA = {"embed", "shorts", "live"}
PARTES_DE_RUTA = 2  # ["embed", "<id>"]


class VideoInvalido(ValueError):
    """La URL no es un enlace de video de YouTube. El mensaje esta listo para mostrarse."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_VIDEO)


def _id_de(host: str, ruta: str, consulta: dict[str, list[str]]) -> str | None:
    partes = [p for p in ruta.split("/") if p]
    if host in HOSTS_CORTOS:
        return partes[0] if partes else None
    if host in HOSTS_YOUTUBE and partes == ["watch"]:
        return (consulta.get("v") or [None])[0]
    if (
        host in HOSTS_YOUTUBE | HOSTS_SIN_COOKIES
        and len(partes) == PARTES_DE_RUTA
        and partes[0] in TIPOS_DE_RUTA
    ):
        return partes[1]
    return None


def _segundos(texto: str | None) -> int | None:
    """ "90", "90s" o "1m30s" -> 90. Un valor ilegible o fuera de rango se ignora (None)."""
    if not texto:
        return None
    texto = texto.strip().lower()
    if texto.isdigit():
        total = int(texto)
    else:
        coincidencia = PATRON_TIEMPO.fullmatch(texto)
        if not coincidencia or not any(coincidencia.groups()):
            return None
        horas, minutos, segundos = (int(g or 0) for g in coincidencia.groups())
        total = horas * 3600 + minutos * 60 + segundos
    return total if total <= VIDEO_INICIO_MAX else None


def extraer_video(url: str) -> tuple[str, int | None]:
    """(id del video, segundo de inicio o None). Lanza VideoInvalido si no es de YouTube.

    Acepta watch?v=, youtu.be/, /embed/, /shorts/ y /live/, con m.youtube.com, music.youtube.com
    o youtube-nocookie.com, y los tiempos t=90, t=1m30s o start=90. Rechaza otros dominios,
    listas sin v= y URLs de mas de 300 caracteres.
    """
    texto = url.strip()
    if not texto or len(texto) > VIDEO_URL_MAX:
        raise VideoInvalido
    if "://" not in texto:
        texto = f"https://{texto}"
    try:
        partes = urlsplit(texto)
        host = (partes.hostname or "").lower()
    except ValueError:
        raise VideoInvalido from None
    if partes.scheme not in {"http", "https"}:
        raise VideoInvalido
    consulta = parse_qs(partes.query)
    video_id = _id_de(host, partes.path, consulta)
    if video_id is None or not PATRON_ID.fullmatch(video_id):
        raise VideoInvalido
    # El tiempo puede venir en la consulta (?t=, ?start=) o en el fragmento (#t=).
    fragmento = parse_qs(partes.fragment)
    for origen in (consulta, fragmento):
        for clave in ("t", "start"):
            segundo = _segundos((origen.get(clave) or [None])[0])
            if segundo is not None:
                return video_id, segundo
    return video_id, None
