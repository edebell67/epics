$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendPath = Join-Path $repoRoot 'frontend'
$frontendUrl = 'http://127.0.0.1:3002'
$readinessUrl = 'http://127.0.0.1:3002/?readinessDemo=1&tab=quarter'

Write-Host 'Starting bizPA tax readiness UI...' -ForegroundColor Cyan

$frontendCommand = "Set-Location '$frontendPath'; `$env:PORT='3002'; npm.cmd start"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand | Out-Null

Write-Host ''
Write-Host 'Tax readiness dashboard URL:' -ForegroundColor Green
Write-Host "  $readinessUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Base frontend URL:' -ForegroundColor Green
Write-Host "  $frontendUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'This launch path uses the local readiness demo state so the active-quarter UI can be reviewed without backend setup.' -ForegroundColor Cyan
