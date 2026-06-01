param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"

function Get-PortProcess {
    param([int]$Port)

    $lines = netstat -ano | Select-String "127\.0\.0\.1:$Port\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = ($line.Line.Trim() -split "\s+")
        if ($parts.Length -ge 5) {
            $pidValue = [int]$parts[-1]
            Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" |
                Select-Object ProcessId, Name, CommandLine
        }
    }
}

function Test-ProjectProcess {
    param(
        [Parameter(Mandatory = $true)]$ProcessInfo,
        [Parameter(Mandatory = $true)][string]$Kind
    )

    $cmd = [string]$ProcessInfo.CommandLine
    if ($Kind -eq "backend") {
        return $cmd -like "*uvicorn*app.main:app*"
    }
    if ($Kind -eq "frontend") {
        return $cmd -like "*next*" -and $cmd -like "*$Frontend*"
    }
    return $false
}

function Ensure-PortFree {
    param(
        [int]$Port,
        [string]$Kind
    )

    $processes = @(Get-PortProcess -Port $Port)
    if ($processes.Count -eq 0) {
        return
    }

    foreach ($processInfo in $processes) {
        if (Test-ProjectProcess -ProcessInfo $processInfo -Kind $Kind) {
            if ($Restart) {
                Write-Host "Stopping existing $Kind on port $Port (PID $($processInfo.ProcessId))."
                Stop-Process -Id $processInfo.ProcessId -Force
                Start-Sleep -Seconds 1
            } else {
                Write-Host "$Kind is already running on port $Port (PID $($processInfo.ProcessId))."
                return
            }
        } else {
            Write-Host "Port $Port is used by another process:"
            Write-Host "PID $($processInfo.ProcessId) $($processInfo.Name)"
            Write-Host $processInfo.CommandLine
            throw "Stop that process or choose a different port."
        }
    }
}

Ensure-PortFree -Port $BackendPort -Kind "backend"
Ensure-PortFree -Port $FrontendPort -Kind "frontend"

$backendStillRunning = @(Get-PortProcess -Port $BackendPort).Count -gt 0
$frontendStillRunning = @(Get-PortProcess -Port $FrontendPort).Count -gt 0

if (-not $backendStillRunning) {
    Write-Host "Starting backend on http://127.0.0.1:$BackendPort"
    Start-Process -FilePath python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
        -WorkingDirectory $Root `
        -WindowStyle Hidden
}

if (-not $frontendStillRunning) {
    Write-Host "Starting frontend on http://127.0.0.1:$FrontendPort"
    Start-Process -FilePath powershell `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "npm run dev" `
        -WorkingDirectory $Frontend `
        -WindowStyle Hidden
}

Write-Host ""
Write-Host "Frontend: http://127.0.0.1:$FrontendPort/login"
Write-Host "Backend:  http://127.0.0.1:$BackendPort/api/v1/health"
Write-Host ""
Write-Host "Use this to restart both project servers:"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -Restart"
