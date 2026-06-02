@echo off
title Deer Hunter - Loading...
color 0A
cls
echo.
echo  =============================================
echo   DEER HUNTER - EXTREME EDITION
echo  =============================================
echo.
echo  Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] Python not found! Please install Python 3.8+
    echo  Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  Checking pygame...
python -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing pygame...
    pip install pygame --quiet
    if %errorlevel% neq 0 (
        color 0C
        echo  [ERROR] Failed to install pygame!
        pause
        exit /b 1
    )
)

echo  Launching game...
echo.
cd /d "%~dp0"
python deer_hunt.py
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo  [ERROR] Game crashed! Press any key to see error...
    pause
    python deer_hunt.py
)
