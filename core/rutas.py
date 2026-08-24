"""Dónde viven los archivos, tanto corriendo el código como empaquetado.

PyInstaller cambia dos cosas a la vez y conviene no confundirlas. Los recursos
de solo lectura —la interfaz web— viajan dentro del ejecutable y se extraen a
una carpeta temporal **distinta en cada arranque**. Lo que la app escribe
—ffmpeg— no puede vivir ahí: se borraría al cerrar y habría que descargarlo
otra vez cada vez. Eso va junto al .exe, que es lo único con una ubicación
estable.

Sin empaquetar las dos son la misma carpeta: la raíz del proyecto.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def empaquetado() -> bool:
    """True si estamos corriendo dentro de un ejecutable de PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def recursos() -> Path:
    """Raíz de lo que la app solo lee (web/)."""
    if empaquetado():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _RAIZ_PROYECTO


def datos() -> Path:
    """Raíz de lo que la app escribe (bin/). Persiste entre arranques."""
    if empaquetado():
        return Path(sys.executable).resolve().parent
    return _RAIZ_PROYECTO
