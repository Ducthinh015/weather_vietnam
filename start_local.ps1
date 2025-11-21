Param(
  [switch]$Background
)

$ErrorActionPreference = "Stop"

# Activate venv if present
if (Test-Path -Path ".venv/Scripts/Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

$env:PYTHONUNBUFFERED = "1"
# Ensure project root is on PYTHONPATH so backend package imports resolve when launched directly
$env:PYTHONPATH = (Get-Location).Path

if ($Background) {
    Write-Host "Starting AgriCast API + scheduler in background (backend/app.py) ..."
    Start-Process -FilePath "python" -ArgumentList "backend/app.py" -WindowStyle Normal
} else {
    Write-Host "Starting AgriCast API + scheduler (backend/app.py) on http://localhost:8000 ..."
    python backend/app.py
}
