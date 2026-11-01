@echo off
title GIRAGROUP BI System - Iniciar Todo
echo ========================================================
echo   Iniciando GIRAGROUP BI System (Todos los Servicios)
echo ========================================================
echo.
docker compose up -d
echo.
echo ========================================================
echo   Estado de los Contenedores:
echo ========================================================
docker compose ps
echo.
echo ========================================================
echo   Plataforma lista en:
echo   - Web Frontend:  http://localhost:5173
echo   - API Backend:   http://localhost:8000/docs
echo ========================================================
pause
