from __future__ import annotations

from typing import Callable

from .formats import VideoInfo, normalize

# noplaylist es imprescindible aqui, no solo al descargar: un enlace con
# ?list= (YouTube genera listas de radio solo con darle a reproducir musica)
# haria que yt-dlp extrajera la lista entera —decenas de videos— para
# devolver uno. La consulta parece colgada cuando en realidad esta
# trabajando de mas.
_OPCIONES = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "noprogress": True,
}

_NO_DISPONIBLE = (
    "private video",
    "is private",
    "video unavailable",
    "has been removed",
    "no longer available",
    "available in your country",
    "sign in to confirm your age",
)


class ProbeError(Exception):
    """Falló la consulta del enlace."""


class UnsupportedSite(ProbeError):
    """El enlace no pertenece a ningún sitio que yt-dlp sepa manejar."""


class VideoUnavailable(ProbeError):
    """El sitio respondió, pero el video no se puede obtener."""


def _traducir(error: Exception) -> ProbeError:
    mensaje = str(error)
    minusculas = mensaje.lower()

    if "unsupported url" in minusculas:
        return UnsupportedSite(
            "Ese enlace no pertenece a ningún sitio soportado."
        )
    if any(pista in minusculas for pista in _NO_DISPONIBLE):
        return VideoUnavailable(mensaje.replace("ERROR: ", "", 1))
    return ProbeError(mensaje.replace("ERROR: ", "", 1))


def probe(
    url: str,
    ydl_factory: Callable | None = None,
    cookies: dict | None = None,
) -> VideoInfo:
    """Consulta qué ofrece un enlace, sin descargar nada.

    `cookies` son opciones de yt-dlp para autenticarse (por ejemplo
    `cookiesfrombrowser`). Muchos sitios bloquean la consulta anónima con
    una verificación anti-bot, así que la autenticación hace falta aquí y
    no solo al descargar.
    """
    if ydl_factory is None:
        from yt_dlp import YoutubeDL

        opciones = dict(_OPCIONES)
        if cookies:
            opciones.update(cookies)
        ydl_factory = lambda: YoutubeDL(opciones)  # noqa: E731

    from yt_dlp.utils import DownloadError

    try:
        with ydl_factory() as ydl:
            crudo = ydl.extract_info(url, download=False)
    except DownloadError as error:
        raise _traducir(error) from error

    if not crudo:
        raise VideoUnavailable("El sitio no devolvió información para ese enlace.")

    return normalize(crudo)
