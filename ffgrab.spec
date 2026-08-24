# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para FFGrab.

    pyinstaller ffgrab.spec

Deja `dist/FFGrab.exe`, un solo archivo sin consola. Notas de las dos cosas
que no salen bien por defecto:

- **yt-dlp** importa sus extractores por nombre, en caliente. El analisis
  estatico de PyInstaller no ve ninguno, asi que el .exe se construye igual y
  falla al consultar cualquier enlace. Por eso van todos como hiddenimports:
  es lo que engorda el ejecutable, y es lo que lo hace funcionar.
- **web/** viaja dentro del .exe como dato; `core.rutas` se encarga de
  encontrarlo alli. ffmpeg **no** viaja: se descarga junto al ejecutable la
  primera vez, porque lo que se extrae del .exe vive en una carpeta temporal
  que desaparece al cerrar.
"""

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[("web", "web")],
    hiddenimports=collect_submodules("yt_dlp") + ["truststore"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FFGrab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
