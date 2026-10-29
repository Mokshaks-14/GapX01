@echo off
title GapX AI Backend Runner
echo ========================================================
echo                 GAPX AI BACKEND RUNNER
echo ========================================================
echo.

cd /d "%~dp0backend"

if not exist venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [INFO] Installing all dependencies from requirements.txt...
python -m pip install -r requirements.txt

echo [INFO] Force-installing critical packages...
python -m pip install "email-validator>=2.0.0" "passlib[bcrypt]" "bcrypt" "python-jose[cryptography]" "pydantic-settings" "pypdf>=3.0.0" "pdfminer.six>=20221105" "reportlab>=4.0.0" --quiet

echo.
echo [SUCCESS] Starting FastAPI server on port 8000...
echo [INFO] API Swagger docs: http://127.0.0.1:8000/docs
echo [INFO] Base URL:         http://127.0.0.1:8000
echo.
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause

