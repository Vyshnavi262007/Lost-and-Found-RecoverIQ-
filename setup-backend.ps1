# Run from the RecoverIQ folder:  powershell -ExecutionPolicy Bypass -File .\setup-backend.ps1
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item ..\.env.example .env; Write-Host "Created backend\.env from .env.example" }
# makemigrations is needed once because migration files were not generated when this project was built
.\.venv\Scripts\python.exe manage.py makemigrations accounts core reports messaging claims adminapi
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
Write-Host "Backend ready. Start it with: .\.venv\Scripts\python.exe manage.py runserver"
