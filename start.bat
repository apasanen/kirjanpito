@echo off
cd /d "%~dp0"
setlocal

set "MODE=docker"
set "PROFILE=%DB_PROFILE%"
if not defined PROFILE set "PROFILE=default"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--nodocker" (
	set "MODE=local"
	shift
	goto parse_args
)
if /I "%~1"=="--profile" (
	if "%~2"=="" (
		echo ERROR: --profile requires a value.
		exit /b 1
	)
	set "PROFILE=%~2"
	shift
	shift
	goto parse_args
)
echo ERROR: Unknown option %~1
echo Usage: start.bat [--nodocker] [--profile NAME]
exit /b 1

:args_done
set "PROFILE=%PROFILE: =_%"
set "PROFILE=%PROFILE:/=_%"
set "PROFILE=%PROFILE:\=_%"
if "%PROFILE%"=="" set "PROFILE=default"

set "DB_PROFILE=%PROFILE%"
if not defined DB_PATH if not defined DATABASE_URL (
	if /I "%PROFILE%"=="default" (
		set "DB_PATH=data\accounting.db"
	) else (
		set "DB_PATH=data\accounting_%PROFILE%.db"
	)
)

if not exist "data" mkdir data
if exist "accounting.db" if not exist "data\accounting.db" move /Y "accounting.db" "data\accounting.db" >nul
if not exist "%DB_PATH%" type nul > "%DB_PATH%"
if not exist "data\receipts" mkdir "data\receipts"
if exist "receipts" move /Y "receipts\*" "data\receipts\" >nul 2>nul

echo Using database profile: %DB_PROFILE%
echo Database file: %DB_PATH%

if /I "%MODE%"=="local" goto run_local

set "COMPOSE_CMD="
docker compose version >nul 2>&1
if %ERRORLEVEL% equ 0 set "COMPOSE_CMD=docker compose"

if not defined COMPOSE_CMD (
	docker-compose version >nul 2>&1
	if %ERRORLEVEL% equ 0 set "COMPOSE_CMD=docker-compose"
)

if not defined COMPOSE_CMD (
	echo ERROR: Docker Compose not found.
	echo Install Docker Desktop and ensure 'docker compose' is available.
	exit /b 1
)

if not exist "split_output" mkdir split_output

echo Starting Accounting Application with Docker...
start http://127.0.0.1:8000
%COMPOSE_CMD% up --build

goto end

:run_local
echo Starting Accounting Application without Docker...
start http://127.0.0.1:8000
.venv\Scripts\uvicorn app.main:app --reload --reload-exclude ".venv/*" --reload-exclude "data/receipts/*" --reload-exclude "split_output/*" --reload-exclude "*.db"

:end

endlocal
