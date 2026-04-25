@echo off
cd /d "%~dp0"
setlocal

if not exist "data" mkdir data
if exist "accounting.db" if not exist "data\accounting.db" move /Y "accounting.db" "data\accounting.db" >nul
if not exist "data\accounting.db" type nul > "data\accounting.db"
if not exist "data\receipts" mkdir "data\receipts"
if exist "receipts" move /Y "receipts\*" "data\receipts\" >nul 2>nul

if /I "%~1"=="--nodocker" goto run_local

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
