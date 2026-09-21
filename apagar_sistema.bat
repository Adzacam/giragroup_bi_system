@echo off
title GIRAGROUP BI System - Apagar Todo
echo ========================================================
echo   Apagando GIRAGROUP BI System...
echo ========================================================
echo.
docker compose down
echo.
echo Todos los contenedores han sido detenidos correctamente.
pause
