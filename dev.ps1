# dev.ps1 — Launch Budgie backend + frontend for local network development
# Usage: .\dev.ps1
# Then connect from iPhone at http://<IP>:5173

$ErrorActionPreference = "Stop"

# Get local network IP — prefer Ethernet/Wi-Fi, skip virtual adapters
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -ne '127.0.0.1' -and
        $_.PrefixOrigin -ne 'WellKnown' -and
        $_.InterfaceAlias -notmatch 'Loopback|Bluetooth|vEthernet|Docker|WSL|VPN|VMware|Hyper-V|Virtual'
    } |
    Sort-Object -Property { if ($_.InterfaceAlias -match 'Ethernet') { 0 } elseif ($_.InterfaceAlias -match 'Wi-Fi') { 1 } else { 2 } } |
    Select-Object -First 1).IPAddress

if (-not $ip) {
    $ip = "localhost"
    Write-Host "  Warning: Could not detect LAN IP" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Budgie Dev Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "  iPhone:   http://${ip}:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Ctrl+C to stop both servers" -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start backend as a background job
$backend = Start-Process -NoNewWindow -PassThru -FilePath "poetry" `
    -ArgumentList "run", "uvicorn", "budgie.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $PSScriptRoot

# Give backend a moment to start
Start-Sleep -Seconds 2

# Start frontend (foreground — Ctrl+C stops this, then we clean up)
try {
    Push-Location "$PSScriptRoot\frontend"
    & npx vite --host --port 5173
}
finally {
    Pop-Location
    # Kill backend when frontend exits
    if ($backend -and -not $backend.HasExited) {
        Write-Host "`nStopping backend..." -ForegroundColor DarkGray
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
        # Also kill any child python processes spawned by uvicorn --reload
        Get-Process -Name python -ErrorAction SilentlyContinue |
            Where-Object { $_.StartTime -ge $backend.StartTime } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done." -ForegroundColor Green
}
