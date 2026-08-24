#!/usr/bin/env python3
"""Lanzador de FFGrab.

En Windows conviven varios Python —el de la Microsoft Store, el de
python.org, entornos virtuales de otras herramientas— y el nombre `python`
puede resolver a cualquiera de ellos segun el PATH del momento. Si resuelve a
uno sin las dependencias instaladas, la ventana abre igual pero consultar un
enlace se queda colgado para siempre, sin decir por que. Es el peor modo de
fallar: la app *parece* funcionar.

Por eso este script no confia en el nombre. Se asegura de que exista un
entorno local en `.venv` con las dependencias dentro, y lanza la app con ese
interprete y no con otro.

    python run.py

Tambien funciona con doble clic. Si el Python que lo abre es demasiado viejo,
busca uno mejor en el sistema en vez de rendirse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
MINIMO = (3, 11)
MODULOS = ("webview", "yt_dlp", "truststore")


def _python_del_entorno(venv: Path) -> Path:
    """Ruta del interprete dentro de un entorno virtual, exista o no."""
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _version_de(comando: list[str]) -> tuple[int, ...] | None:
    """Version real del interprete, o None si no responde como tal.

    Preguntarle al propio binario es lo unico que distingue un Python de
    verdad del atajo de la Microsoft Store, que existe en el PATH pero no
    ejecuta nada hasta que instalas algo. Recibe una lista porque algunos
    candidatos son lanzadores que necesitan un argumento (`py -3`).
    """
    try:
        salida = subprocess.run(
            comando + ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if salida.returncode != 0:
        return None
    try:
        return tuple(int(x) for x in salida.stdout.strip().split("."))
    except ValueError:
        return None


def _candidatos_base() -> list[list[str]]:
    """Interpretes que podrian servir para crear el entorno, en orden.

    El primero es el que esta corriendo este mismo script: si sirve, no hay
    nada que buscar.
    """
    lista: list[list[str]] = [[sys.executable]]
    if os.name == "nt":
        lista += [["py", "-3"], ["python"], ["python3"]]
        for base in (
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
            Path(os.environ.get("PROGRAMFILES", "")) / "Python",
            Path("C:/"),
        ):
            if not base.is_dir():
                continue
            for carpeta in sorted(base.glob("Python3*"), reverse=True):
                exe = carpeta / "python.exe"
                if exe.exists():
                    lista.append([str(exe)])
    else:
        lista += [["python3"], ["python"]]
    return lista


def _elegir_base() -> list[str] | None:
    vistos = set()
    for candidato in _candidatos_base():
        clave = tuple(candidato)
        if clave in vistos:
            continue
        vistos.add(clave)
        version = _version_de(candidato)
        if version and version >= MINIMO:
            return candidato
    return None


def _faltan_dependencias(python: Path) -> bool:
    orden = "; ".join(f"import {m}" for m in MODULOS)
    try:
        hecho = subprocess.run(
            [str(python), "-c", orden], capture_output=True, timeout=120
        )
    except (OSError, subprocess.SubprocessError):
        return True
    return hecho.returncode != 0


def _preparar_entorno() -> Path:
    """Devuelve el interprete listo para correr la app. Lanza si no se puede."""
    python = _python_del_entorno(VENV)

    if not python.exists():
        base = _elegir_base()
        if base is None:
            raise RuntimeError(
                f"No encontre un Python {MINIMO[0]}.{MINIMO[1]} o superior.\n"
                "Instalalo desde https://www.python.org/downloads/ y volve a intentarlo."
            )
        print(f"Creando entorno local en .venv con {' '.join(base)} ...")
        subprocess.run(base + ["-m", "venv", str(VENV)], check=True)
        if not python.exists():
            raise RuntimeError(f"No se pudo crear el entorno con {' '.join(base)}.")

    if _faltan_dependencias(python):
        print("Instalando dependencias ...")
        subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(RAIZ / "requirements.txt")],
            check=True,
        )
        if _faltan_dependencias(python):
            raise RuntimeError("Fallo la instalacion de dependencias.")

    return python


def main() -> int:
    try:
        python = _preparar_entorno()
    except Exception as error:
        print(f"\n{error}\n", file=sys.stderr)
        _esperar_si_doble_clic()
        return 1

    return subprocess.run([str(python), str(RAIZ / "app.py")]).returncode


def _esperar_si_doble_clic() -> None:
    """Mantiene la consola abierta para que el error se pueda leer.

    Con doble clic la ventana se cierra en cuanto termina el proceso, asi que
    el mensaje de error aparece y desaparece en el mismo instante.
    """
    if sys.stdin and sys.stdin.isatty():
        try:
            input("Presiona Enter para salir...")
        except EOFError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
