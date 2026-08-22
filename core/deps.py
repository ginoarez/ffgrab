from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "bin"


class FFmpegState(Enum):
    FOUND = "found"
    MISSING = "missing"
    BROKEN = "broken"


@dataclass(frozen=True)
class FFmpegStatus:
    state: FFmpegState
    path: Path | None = None
    version: str | None = None


def _verify(exe: Path) -> str | None:
    """Devuelve la línea de versión si el binario responde, None si está roto."""
    try:
        result = subprocess.run(
            [str(exe), "-version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout.splitlines()[0].strip() or None


def ffmpeg_status(
    bundled_dir: Path | None = None,
    verifier: Callable[[Path], str | None] | None = None,
) -> FFmpegStatus:
    """Busca ffmpeg primero en la carpeta local, después en el PATH del sistema.

    Un binario presente pero que no responde se reporta BROKEN, nunca FOUND.
    """
    check = verifier or _verify
    directorio = bundled_dir if bundled_dir is not None else BUNDLED_DIR

    candidatos = [directorio / "ffmpeg.exe", directorio / "ffmpeg"]
    del_sistema = shutil.which("ffmpeg")
    if del_sistema:
        candidatos.append(Path(del_sistema))

    hubo_alguno = False
    for candidato in candidatos:
        if not candidato.exists():
            continue
        hubo_alguno = True
        version = check(candidato)
        if version:
            return FFmpegStatus(FFmpegState.FOUND, candidato, version)

    if hubo_alguno:
        return FFmpegStatus(FFmpegState.BROKEN)
    return FFmpegStatus(FFmpegState.MISSING)


FFMPEG_URL_WINDOWS = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.zip"
)
_PYPI_YTDLP = "https://pypi.org/pypi/yt-dlp/json"


def _descargar(url: str, hacia: Path, on_progress: Callable[[float], None]) -> Path:
    hacia.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as respuesta:
        total = int(respuesta.headers.get("Content-Length") or 0)
        bajados = 0
        with open(hacia, "wb") as salida:
            while True:
                trozo = respuesta.read(65536)
                if not trozo:
                    break
                salida.write(trozo)
                bajados += len(trozo)
                if total:
                    on_progress(bajados / total * 100)
    on_progress(100.0)
    return hacia


def install_ffmpeg(
    on_progress: Callable[[float], None],
    dest_dir: Path | None = None,
    downloader: Callable[[str, Path, Callable[[float], None]], Path] | None = None,
) -> Path:
    """Descarga ffmpeg, extrae los binarios y devuelve la ruta al ejecutable.

    El zip oficial guarda los binarios dentro de un subdirectorio con versión en
    el nombre, así que se aplana: solo interesan los .exe, no el árbol.
    """
    destino = dest_dir if dest_dir is not None else BUNDLED_DIR
    destino.mkdir(parents=True, exist_ok=True)
    bajar = downloader or _descargar

    archivo_zip = destino / "_ffmpeg_descarga.zip"
    bajar(FFMPEG_URL_WINDOWS, archivo_zip, on_progress)

    encontrado: Path | None = None
    try:
        with zipfile.ZipFile(archivo_zip) as z:
            for miembro in z.namelist():
                nombre = Path(miembro).name
                if nombre.lower() not in ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"):
                    continue
                salida = destino / nombre
                with z.open(miembro) as origen, open(salida, "wb") as fin:
                    shutil.copyfileobj(origen, fin)
                if nombre.lower().startswith("ffmpeg"):
                    encontrado = salida
    finally:
        archivo_zip.unlink(missing_ok=True)

    if encontrado is None:
        raise RuntimeError("El archivo descargado no contenía ffmpeg.")
    return encontrado


def ytdlp_update_available(
    installed: str | None = None,
    fetcher: Callable[[], str] | None = None,
) -> str | None:
    """Devuelve la versión nueva disponible, o None si está al día o no hay red.

    Nunca lanza excepción: no poder consultar no debe impedir usar la app.
    """
    if installed is None:
        try:
            from yt_dlp.version import __version__ as installed
        except ImportError:
            return None

    consultar = fetcher or _ultima_version_pypi
    try:
        ultima = consultar()
    except Exception:
        return None

    return ultima if ultima and ultima != installed else None


def _ultima_version_pypi() -> str:
    with urllib.request.urlopen(_PYPI_YTDLP, timeout=10) as respuesta:
        return json.load(respuesta)["info"]["version"]
