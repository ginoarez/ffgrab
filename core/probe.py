from __future__ import annotations

from typing import Callable

from .formats import VideoInfo, normalize

_OPCIONES = {"quiet": True, "no_warnings": True, "skip_download": True}

_NO_DISPONIBLE = (
    "private video",
    "video unavailable",
    "has been removed",
    "no longer available",
    "not available in your country",
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


def probe(url: str, ydl_factory: Callable | None = None) -> VideoInfo:
    """Consulta qué ofrece un enlace, sin descargar nada."""
    if ydl_factory is None:
        from yt_dlp import YoutubeDL

        ydl_factory = lambda: YoutubeDL(_OPCIONES)  # noqa: E731

    from yt_dlp.utils import DownloadError

    try:
        with ydl_factory() as ydl:
            crudo = ydl.extract_info(url, download=False)
    except DownloadError as error:
        raise _traducir(error) from error

    if not crudo:
        raise VideoUnavailable("El sitio no devolvió información para ese enlace.")

    return normalize(crudo)
