@echo off
title EGE-TUTOR // BACKEND

cd /d "%~dp0"

echo ============================================
echo   EGE-TUTOR // BACKEND
echo ============================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] venv not found. Create it first:
    echo     python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo [ERROR] uvicorn not installed in venv. Run:
    echo     pip install fastapi uvicorn sqlalchemy
    pause
    exit /b 1
)

echo [OK] venv activated
echo [OK] uvicorn found
echo.
echo Server: http://127.0.0.1:8000
echo Docs:   http://127.0.0.1:8000/docs
echo.
echo To stop: close this window or press Ctrl+C
echo ============================================
echo.

python -m uvicorn main:app --reload

pause