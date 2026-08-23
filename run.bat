@echo off
rem Lanzador de FFGrab.
rem
rem En Windows conviven varios Python (el de la Microsoft Store, el de
rem python.org, entornos virtuales de otras herramientas) y el nombre "python"
rem puede resolver a cualquiera de ellos segun el PATH del momento. Si resuelve
rem a uno sin las dependencias, la ventana abre igual pero consultar un enlace
rem se queda colgado para siempre, sin decir por que.
rem
rem Por eso este script no confia en el nombre: prueba candidatos y comprueba
rem que cada uno sea de verdad un Python 3.11 o superior antes de usarlo.

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PY="

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
    goto :tiene_entorno
)

echo Buscando un Python utilizable...
for %%C in ("py -3" "python3" "python") do (
    if not defined PY (
        for /f "delims=" %%V in ('%%~C -c "import sys; print(1 if sys.version_info>=(3,11) else 0)" 2^>nul') do (
            if "%%V"=="1" (
                set "BASE=%%~C"
                echo   usando: %%~C
            )
        )
    )
)

if not defined BASE (
    echo.
    echo No encontre un Python 3.11 o superior.
    echo Instalalo desde https://www.python.org/downloads/ y vuelve a intentarlo.
    echo.
    pause
    exit /b 1
)

echo Creando entorno local en .venv ...
%BASE% -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo No se pudo crear el entorno con %BASE%.
    echo.
    pause
    exit /b 1
)
set "PY=.venv\Scripts\python.exe"

:tiene_entorno
"%PY%" -c "import webview, yt_dlp, truststore" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias ...
    "%PY%" -m pip install --upgrade pip --quiet
    "%PY%" -m pip install -r requirements.txt --quiet
    "%PY%" -c "import webview, yt_dlp, truststore" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo Fallo la instalacion de dependencias.
        echo.
        pause
        exit /b 1
    )
)

"%PY%" app.py
