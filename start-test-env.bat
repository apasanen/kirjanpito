@echo off
REM Test Environment Startup Script for Kirjanpito-ohjelma
REM Windows Version

setlocal enabledelayedexpansion

echo.
echo ====================================
echo Kirjanpito-ohjelma Test Environment
echo ====================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment found
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -r requirements.txt > nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Failed to install dependencies
    echo Trying with --no-cache-dir...
    pip install --no-cache-dir -r requirements.txt
    if !errorlevel! neq 0 (
        echo ERROR: Still failed to install dependencies
        exit /b 1
    )
)

REM Start server
echo [4/4] Starting FastAPI server...
echo.
echo ====================================
echo Server running at:
echo   http://127.0.0.1:8000
echo
echo Default views:
echo   - Expenses:  http://127.0.0.1:8000/expenses/
echo   - Categories: http://127.0.0.1:8000/categories/
echo   - Reports:   http://127.0.0.1:8000/reports/yearly?cost_center_id=1^&year=2026
echo
echo Press Ctrl+C to stop
echo ====================================
echo.

.venv\Scripts\uvicorn app.main:app --reload

endlocal
