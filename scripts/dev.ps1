$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontend = Join-Path $root "frontend"
$backendPython = Join-Path $root ".venv313\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
  $backendPython = "python"
}

$backendCommand = "Set-Location `"$root`"; `$env:PYTHONPATH=`"$root`"; & `"$backendPython`" -m uvicorn backend.server:app --host 127.0.0.1 --port 8001"
$frontendCommand = "Set-Location `"$frontend`"; npm.cmd run dev -- --hostname 127.0.0.1 --port 3000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host "Backend:  http://127.0.0.1:8001"
Write-Host "Frontend: http://127.0.0.1:3000"
Write-Host ""
Write-Host "If the backend window reports missing modules, run:"
Write-Host "python -m pip install -r backend\requirements.txt"
