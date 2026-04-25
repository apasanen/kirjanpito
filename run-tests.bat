@echo off
REM Quick test runner for Kirjanpito-ohjelma
REM Usage: run-tests.bat [pytest-args]

setlocal enabledelayedexpansion

echo.
echo === Kirjanpito-ohjelma Test Runner ===
echo.

REM Activate venv
call .venv\Scripts\Activate.ps1 >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Trying PowerShell activation...
    powershell -Command ".\.venv\Scripts\Activate.ps1" >nul 2>&1
)

REM Check if pytest is installed
.venv\Scripts\pip show pytest >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing test dependencies...
    call .venv\Scripts\pip install pytest pytest-asyncio httpx -q
)

echo [RUN] pytest %*
echo.

REM Run tests with any additional arguments
if "%1"=="" (
    call .venv\Scripts\pytest tests/ -v --tb=short
) else (
    call .venv\Scripts\pytest %*
)

set TEST_EXIT=%ERRORLEVEL%

echo.
if %TEST_EXIT% equ 0 (
    echo [OK] All tests passed!
    exit /b 0
) else (
    echo [FAIL] Some tests failed (exit code: %TEST_EXIT%)
    exit /b %TEST_EXIT%
)
