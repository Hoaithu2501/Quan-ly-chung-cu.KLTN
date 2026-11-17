param(
    [ValidateSet('Docker', 'Python')]
    [string]$Mode = 'Docker'
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Mode -eq 'Docker') {
    Write-Host 'Starting Docker. Database: /app/data/QLCC.db in the Compose data volume.'
    & docker compose up --build -d
    if ($LASTEXITCODE -ne 0) { throw 'Cannot start Docker. Check Docker Desktop; no Python fallback was started.' }
    Write-Host 'Open http://localhost:5000. Desktop and iPhone use the same database.'
    return
}

Write-Warning 'Python mode uses the separate DATABASE_PATH from .env, not the Docker database. Use this mode only for local development.'
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python virtual environment.' }
}
& .venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Cannot install dependencies.' }
& .venv/Scripts/python.exe scripts/init_db.py --demo
if ($LASTEXITCODE -ne 0) { throw 'Cannot initialize database.' }
& .venv/Scripts/python.exe scripts/run.py
