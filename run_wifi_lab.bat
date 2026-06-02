@echo off
title WiFi Lab Suite v3.0
color 0A
mode con: cols=120 lines=50
cls
echo.
echo  [*] WiFi Security Lab Suite v3.0
echo  [*] Educational use only - authorized testing only
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [!] Python not found.
    pause & exit /b 1
)

cd /d "%~dp0"
python wifi_lab.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] Error occurred.
    pause
)
