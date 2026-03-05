$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run this first:"
    Write-Host "  .\scripts\first_run_windows.ps1"
    exit 1
}

& .\.venv\Scripts\python.exe -m app.main
