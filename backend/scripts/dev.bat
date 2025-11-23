@echo off
REM AIPanel Backend - Windows Development Script
REM Usage: dev.bat [command]

setlocal enabledelayedexpansion

set BACKEND_DIR=%~dp0..
cd /d %BACKEND_DIR%

if "%1"=="" goto run
if "%1"=="run" goto run
if "%1"=="setup" goto setup
if "%1"=="migrate" goto migrate
if "%1"=="test" goto test
if "%1"=="help" goto help
goto help

:setup
echo [AIPanel] Setting up backend...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if exist "requirements-dev.txt" pip install -r requirements-dev.txt
echo [AIPanel] Setup complete!
goto end

:run
echo [AIPanel] Starting development server...
if not exist "venv" (
    echo ERROR: Virtual environment not found. Run: dev.bat setup
    goto end
)
call venv\Scripts\activate.bat
echo API Docs: http://localhost:8000/api/docs
echo Health:   http://localhost:8000/health
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
goto end

:migrate
echo [AIPanel] Running migrations...
call venv\Scripts\activate.bat
alembic upgrade head
goto end

:test
echo [AIPanel] Running tests...
call venv\Scripts\activate.bat
pytest tests/ -v
goto end

:help
echo.
echo AIPanel Backend - Development Script (Windows)
echo.
echo Usage: dev.bat [command]
echo.
echo Commands:
echo   setup     Install dependencies and create virtual environment
echo   run       Start development server (default)
echo   migrate   Run database migrations
echo   test      Run tests
echo   help      Show this help
echo.
echo Quick Start:
echo   1. dev.bat setup
echo   2. dev.bat run
echo.
goto end

:end
endlocal
