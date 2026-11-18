@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno de Python...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo No se pudo crear el entorno. Instala Python 3.11 o posterior.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Instalando Pygame-ce. Este paso necesita internet...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo No se pudo instalar Pygame-ce. Revisa tu conexion.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
