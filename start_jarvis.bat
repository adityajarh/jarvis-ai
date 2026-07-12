@echo off
cd /d "%~dp0"
title JARVIS Server

echo Starting JARVIS...
echo.

start "JARVIS Server" cmd /k "python app.py"

timeout /t 3 /nobreak >nul

start http://127.0.0.1:5000