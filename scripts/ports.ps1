$ErrorActionPreference = "Stop"

foreach ($port in 3000, 8000) {
    Write-Host "Port $port"
    $lines = netstat -ano | Select-String "127\.0\.0\.1:$port\s+.*LISTENING"
    if (-not $lines) {
        Write-Host "  free"
        continue
    }
    foreach ($line in $lines) {
        $parts = ($line.Line.Trim() -split "\s+")
        $pidValue = [int]$parts[-1]
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue"
        Write-Host "  PID $($processInfo.ProcessId) $($processInfo.Name)"
        Write-Host "  $($processInfo.CommandLine)"
    }
}
