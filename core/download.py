from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Callable

# Margen sobre el tamaño estimado: los archivos temporales de yt-dlp y el
# remuxeo de ffmpeg ocupan más que el resultado final.
_MARGEN = 1.5


class DestinationError(Exception):
    """La carpeta de destino no sirve: no se puede escribir o no hay espacio."""


def ensure_writable(
    outdir: Path,
    needed_bytes: int = 0,
    usage: Callable[[Path], object] | None = None,
) -> None:
    """Comprueba el destino ANTES de empezar a descargar.

    Descubrir a mitad de un archivo de 4 GB que no había espacio, o que la
    carpeta era de solo lectura, es el peor momento posible para enterarse.
    """
    outdir = Path(outdir)
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as error:
        raise DestinationError(
            f"No se puede usar la carpeta de destino: {error}"
        ) from error

    if not outdir.is_dir():
        raise DestinationError(f"La ruta de destino no es una carpeta: {outdir}")

    try:
        with tempfile.NamedTemporaryFile(dir=str(outdir), suffix=".ffgrab-test"):
            pass
    except (OSError, PermissionError) as error:
        raise DestinationError(
            f"Sin permiso de escritura en {outdir}: {error}"
        ) from error

    if not needed_bytes:
        return

    medir = usage or shutil.disk_usage
    try:
        libre = medir(outdir).free
    except OSError:
        return  # no poder medir no debe impedir intentarlo

    requerido = int(needed_bytes * _MARGEN)
    if libre < requerido:
        raise DestinationError(
            f"No hay espacio suficiente: hacen falta unos "
            f"{requerido // 1048576} MB y quedan {libre // 1048576} MB."
        )


def build_opts(options: dict, ffmpeg_path: str, outdir: Path) -> dict:
    """Traduce las opciones elegidas en la interfaz a opciones de yt-dlp.

    Función pura: no toca red ni disco, así que se prueba entera sin descargar.
    """
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": str(ffmpeg_path),
        "outtmpl": str(Path(outdir) / "%(title)s.%(ext)s"),
    }

    if options["mode"] == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.get("audio_format", "mp3"),
            }
        ]
        return opts

    video = options["video_format_id"]
    audio = options.get("audio_format_id")
    opts["format"] = f"{video}+{audio}" if audio else video
    opts["merge_output_format"] = options.get("container", "mp4")

    idioma = options.get("subtitle_lang")
    if not idioma:
        return opts

    opts["subtitleslangs"] = [idioma]
    opts["subtitlesformat"] = "srt"
    if options.get("subtitle_auto"):
        opts["writeautomaticsub"] = True
    else:
        opts["writesubtitles"] = True

    if options.get("embed_subs", True):
        opts["postprocessors"] = [
            {
                "key": "FFmpegEmbedSubtitle",
                # Con already_have_subtitle=True yt-dlp incrusta la pista y
                # además deja el .srt en disco en vez de borrarlo.
                "already_have_subtitle": bool(options.get("keep_srt", True)),
            }
        ]

    return opts


def run(
    job,
    on_progress: Callable[[float, str], None],
    ffmpeg_path: str,
    outdir: Path,
    ydl_factory: Callable[[dict], object] | None = None,
) -> str:
    """Ejecuta UNA descarga. Devuelve la ruta del archivo final.

    Si on_progress lanza JobCancelled, la excepción sube y aborta la descarga.
    """
    ensure_writable(outdir, needed_bytes=job.options.get("filesize_approx") or 0)

    opts = build_opts(job.options, ffmpeg_path, outdir)
    resultado: dict[str, str] = {}

    def hook(datos: dict) -> None:
        if datos.get("status") == "downloading":
            total = datos.get("total_bytes") or datos.get("total_bytes_estimate") or 0
            bajados = datos.get("downloaded_bytes") or 0
            porcentaje = (bajados / total * 100) if total else 0.0
            on_progress(porcentaje, (datos.get("_speed_str") or "").strip())
        elif datos.get("status") == "finished":
            resultado["path"] = datos.get("filename") or ""

    opts["progress_hooks"] = [hook]

    if ydl_factory is None:
        from yt_dlp import YoutubeDL

        ydl_factory = YoutubeDL

    with ydl_factory(opts) as ydl:
        ydl.extract_info(job.url, download=True)

    return resultado.get("path", "")
