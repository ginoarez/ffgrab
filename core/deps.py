from __future__ import annotations

import shutil
import subprocess
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
