@echo off
title WiFi Recon Tool v2.0
color 0A
mode con: cols=120 lines=45
cls

echo.
echo  [*] Checking environment...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [!] Python not found. Install from https://www.python.org/downloads/
    pause & exit /b 1
)

echo  [*] Launching WiFi Recon Tool...
echo.
timeout /t 1 /nobreak >nul

cd /d "%~dp0"
python wifi_scan.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo  [!] Tool exited with an error.
    pause
)
