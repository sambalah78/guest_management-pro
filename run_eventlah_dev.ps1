# EventLah development launcher
# One terminal: Reflex app + durable email worker.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
$WorkerStdout = Join-Path $LogDir "email_worker.stdout.log"
$WorkerStderr = Join-Path $LogDir "email_worker.stderr.log"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found: $Python"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Write-Host "Starting EventLah email worker..."
$worker = Start-Process `
    -FilePath $Python `
    -ArgumentList @("-m", "guest_management.workers.email_worker") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $WorkerStdout `
    -RedirectStandardError $WorkerStderr `
    -PassThru

Write-Host "Email worker PID: $($worker.Id)"
Write-Host "Worker logs: $LogDir"
Write-Host ""
Write-Host "Starting Reflex..."
Write-Host ""

try {
    & $Python -m reflex run
}
finally {
    if ($worker -and -not $worker.HasExited) {
        Write-Host ""
        Write-Host "Stopping EventLah email worker PID $($worker.Id)..."
        Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Host "EventLah development session stopped."
}