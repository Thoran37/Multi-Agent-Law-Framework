<#
PowerShell helper to create venv, install backend deps, and start the FastAPI server.
Usage: Open PowerShell in the repo root and run `.
un-backend.ps1`.
#>

# Change to script directory (repo root)
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $here

Write-Host "Setting up virtual environment and starting backend..."

# Create venv if missing
if (-not (Test-Path .\.venv)) {
    Write-Host "Creating virtual environment .venv..."
    python -m venv .venv
}

# Activate venv in this session
Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements (backend/requirements.txt)..."
pip install --upgrade pip
pip install -r backend\requirements.txt

Write-Host "Starting Uvicorn (FastAPI) on http://127.0.0.1:8000"
python -m uvicorn backend.server:app --reload --host 127.0.0.1 --port 8000
