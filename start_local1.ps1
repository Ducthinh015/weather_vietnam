Param(
  [switch]$Background
)

$ErrorActionPreference = "Stop"

# Activate venv if present
if (Test-Path -Path ".venv/Scripts/Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

# Ensure clean env for pumping into Mongo
# - Do NOT disable DB inserts
Remove-Item Env:DISABLE_WEATHER_DB -ErrorAction SilentlyContinue
# - Do NOT write to Sheets (not used anymore, but unset for safety)
Remove-Item Env:DISABLE_SHEETS -ErrorAction SilentlyContinue
# - Disable app scheduler if later you start app in same session (optional)
$env:DISABLE_SCHEDULER = "true"

# Make sure Python sees project root so relative imports work
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = (Get-Location).Path

Write-Host "Starting data pumping to Mongo for all provinces (target 2000 docs each)..."
Write-Host "This may take a long time. You can stop with Ctrl+C."

if ($Background) {
    Start-Process -FilePath "python" -ArgumentList "backend/bootstrap_collect.py" -WindowStyle Normal
    Write-Host "Started in background. Use 'Get-Process python' to see PIDs."
} else {
    python backend/bootstrap_collect.py
}
