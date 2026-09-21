@echo off
title GIRAGROUP BI System - Reconstruir Todo
echo ========================================================
echo   Reconstruyendo Imagenes y Levantando Todo el Sistema...
echo ========================================================
echo.
docker compose up --build -d
echo.
echo ========================================================
echo   Estado de los Contenedores:
echo ========================================================
docker compose ps
echo.
echo Reconstruccion completada. Puedes entrar a http://localhost:5173
pause
