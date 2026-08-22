from __future__ import annotations

from dataclasses import dataclass

# Orden de preferencia: compatibilidad antes que tamaño. Un archivo más grande
# que se reproduce en cualquier reproductor vale más que uno pequeño que no.
_ORDEN_VCODEC = ("avc1", "h264", "vp9", "vp09", "av01")

_SIN_VALOR = (None, "none", "")


@dataclass(frozen=True)
class QualityOption:
    height: int
    label: str
    fps: int
    ext: str
    video_format_id: str
    audio_format_id: str | None
    needs_merge: bool
    filesize_approx: int | None


@dataclass(frozen=True)
class SubtitleTrack:
    lang_code: str
    lang_name: str
    is_auto: bool


@dataclass(frozen=True)
class VideoInfo:
    id: str
    title: str
    duration: int
    thumbnail_url: str
    uploader: str
    qualities: tuple[QualityOption, ...]
    subtitles: tuple[SubtitleTrack, ...]


def _rango_vcodec(vcodec: str | None) -> int:
    valor = (vcodec or "").lower()
    for indice, prefijo in enumerate(_ORDEN_VCODEC):
        if valor.startswith(prefijo):
            return indice
    return len(_ORDEN_VCODEC)


def _tiene_video(f: dict) -> bool:
    return f.get("vcodec") not in _SIN_VALOR


def _tiene_audio(f: dict) -> bool:
    return f.get("acodec") not in _SIN_VALOR


def _mejor_audio(formats: list[dict]) -> dict | None:
    candidatos = [f for f in formats if _tiene_audio(f) and not _tiene_video(f)]
    if not candidatos:
        return None
    return max(candidatos, key=lambda f: f.get("abr") or f.get("tbr") or 0)


def _es_mejor(candidato: dict, actual: dict) -> bool:
    rango_c = _rango_vcodec(candidato.get("vcodec"))
    rango_a = _rango_vcodec(actual.get("vcodec"))
    if rango_c != rango_a:
        return rango_c < rango_a
    return (candidato.get("tbr") or 0) > (actual.get("tbr") or 0)


def _calidades(formats: list[dict]) -> tuple[QualityOption, ...]:
    audio = _mejor_audio(formats)

    por_altura: dict[int, dict] = {}
    for f in formats:
        if not _tiene_video(f) or not f.get("height"):
            continue
        altura = int(f["height"])
        actual = por_altura.get(altura)
        if actual is None or _es_mejor(f, actual):
            por_altura[altura] = f

    opciones = []
    for altura in sorted(por_altura, reverse=True):
        f = por_altura[altura]
        trae_audio = _tiene_audio(f)
        if not trae_audio and audio is None:
            continue  # sin audio emparejable: la opción sería un video mudo

        fps = int(f.get("fps") or 0)
        opciones.append(
            QualityOption(
                height=altura,
                label=f"{altura}p{fps}" if fps > 30 else f"{altura}p",
                fps=fps,
                ext=f.get("ext") or "mp4",
                video_format_id=f["format_id"],
                audio_format_id=None if trae_audio else audio["format_id"],
                needs_merge=not trae_audio,
                filesize_approx=f.get("filesize") or f.get("filesize_approx"),
            )
        )
    return tuple(opciones)


def normalize(raw: dict) -> VideoInfo:
    """Traduce el diccionario crudo de yt-dlp a algo que una interfaz pueda pintar."""
    formats = raw.get("formats") or []
    return VideoInfo(
        id=raw.get("id") or "",
        title=raw.get("title") or "",
        duration=int(raw.get("duration") or 0),
        thumbnail_url=raw.get("thumbnail") or "",
        uploader=raw.get("uploader") or "",
        qualities=_calidades(formats),
        subtitles=(),  # Task 4
    )
