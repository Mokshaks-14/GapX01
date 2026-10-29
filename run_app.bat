@echo off
title GapX AI Unified Launcher
echo ========================================================
echo                 GAPX AI UNIFIED LAUNCHER
echo ========================================================
echo.
echo [INFO] Starting Backend (FastAPI) in a new window...
start "GapX Backend" cmd /c "%~dp0start_backend.bat"

echo [INFO] Starting Frontend (Next.js) in a new window...
start "GapX Frontend" cmd /c "%~dp0start_frontend.bat"

echo.
echo [SUCCESS] Both modules are launching in separate windows!
echo   - Backend API Dashboard: http://localhost:8000/docs
echo   - Frontend SaaS Platform: http://localhost:3000
echo.
echo This launcher window will close automatically in 5 seconds...
timeout /t 5 >nul
exit
