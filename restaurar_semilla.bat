@echo off
title GIRAGROUP BI System - Restaurar Semilla Pre-Defensa
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restaurar_semilla.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] La restauracion de semilla fallo.
    pause
    exit /b 1
)
echo.
pause
