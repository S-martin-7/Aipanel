# AIPanel Backend - Windows PowerShell Development Script
# Usage: .\scripts\dev.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "run"
)

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path -Parent $PSScriptRoot
Set-Location $BackendDir

function Write-Header {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║     AIPanel Backend - Dev Server       ║" -ForegroundColor Blue
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Blue
}

function Test-Venv {
    if (-not (Test-Path "venv")) {
        Write-Host "ERROR: Virtual environment not found." -ForegroundColor Red
        Write-Host "Run: .\scripts\dev.ps1 setup" -ForegroundColor Yellow
        exit 1
    }
}

function Invoke-Setup {
    Write-Header
    Write-Host "Setting up backend..." -ForegroundColor Yellow

    if (-not (Test-Path "venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Cyan
        python -m venv venv
    }

    & "venv\Scripts\Activate.ps1"

    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    pip install -r requirements.txt

    if (Test-Path "requirements-dev.txt") {
        pip install -r requirements-dev.txt
    }

    Write-Host "`n✓ Setup complete!" -ForegroundColor Green
    Write-Host "Run: .\scripts\dev.ps1 run" -ForegroundColor Cyan
}

function Invoke-Run {
    Write-Header
    Test-Venv

    & "venv\Scripts\Activate.ps1"

    Write-Host "Starting development server..." -ForegroundColor Green
    Write-Host "API Docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
    Write-Host "Health:   http://localhost:8000/health" -ForegroundColor Cyan
    Write-Host ""

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

function Invoke-Migrate {
    Test-Venv
    & "venv\Scripts\Activate.ps1"

    Write-Host "Running migrations..." -ForegroundColor Yellow
    alembic upgrade head
    Write-Host "✓ Migrations complete!" -ForegroundColor Green
}

function Invoke-Test {
    Test-Venv
    & "venv\Scripts\Activate.ps1"

    Write-Host "Running tests..." -ForegroundColor Yellow
    pytest tests/ -v
}

function Show-Help {
    Write-Host "`nAIPanel Backend - Development Script (PowerShell)" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1 [command]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup     " -NoNewline -ForegroundColor Green
    Write-Host "Install dependencies and create virtual environment"
    Write-Host "  run       " -NoNewline -ForegroundColor Green
    Write-Host "Start development server (default)"
    Write-Host "  migrate   " -NoNewline -ForegroundColor Green
    Write-Host "Run database migrations"
    Write-Host "  test      " -NoNewline -ForegroundColor Green
    Write-Host "Run tests"
    Write-Host "  help      " -NoNewline -ForegroundColor Green
    Write-Host "Show this help"
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Yellow
    Write-Host "  1. .\scripts\dev.ps1 setup"
    Write-Host "  2. .\scripts\dev.ps1 run"
    Write-Host ""
}

# Main
switch ($Command.ToLower()) {
    "setup"   { Invoke-Setup }
    "run"     { Invoke-Run }
    "migrate" { Invoke-Migrate }
    "test"    { Invoke-Test }
    "help"    { Show-Help }
    default   { Invoke-Run }
}
