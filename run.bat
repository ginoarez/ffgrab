@echo off
rem Lanzador de FFGrab.
rem
rem Existe porque en Windows conviven varios Python (el de la Store, el de
rem python.org, entornos virtuales) y "python app.py" puede resolver a uno que
rem no tiene las dependencias instaladas. El sintoma es cruel: la ventana abre,
rem pero consultar un enlace se queda colgado para siempre. Este script fija el
rem interprete y se asegura de que tenga lo que necesita.

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno local en .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo.
        echo No se pudo crear el entorno. Necesitas Python 3.11 o superior.
        pause
        exit /b 1
    )
)

set PY=.venv\Scripts\python.exe

"%PY%" -c "import webview, yt_dlp, truststore" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias ...
    "%PY%" -m pip install --upgrade pip --quiet
    "%PY%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
)

"%PY%" app.py
