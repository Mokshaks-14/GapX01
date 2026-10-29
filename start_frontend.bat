@echo off
title GapX AI Frontend Runner
echo ========================================================
echo                 GAPX AI FRONTEND RUNNER
echo ========================================================
echo.

cd /d "%~dp0frontend"

if not exist node_modules (
    echo [INFO] Installing NPM packages...
    call npm install
)

echo.
echo [SUCCESS] Starting Next.js Dev Server on http://localhost:3000
echo.
call npm run dev
pause
