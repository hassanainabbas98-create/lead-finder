@echo off
title Business Opportunity Finder & Lead Engine
cd /d "%~dp0"

echo ========================================================
echo       BUSINESS OPPORTUNITY FINDER & LEAD ENGINE
echo ========================================================
echo.
echo Starting server...
echo Access on this laptop : http://127.0.0.1:8000
echo Access on mobile/Wi-Fi: http://172.26.5.3:8000
echo.
echo (Press CTRL+C anytime to stop the server)
echo.

start http://127.0.0.1:8000
.\venv\Scripts\python.exe run.py
pause
