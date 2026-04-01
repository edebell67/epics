$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendPath = Join-Path $repoRoot 'frontend'
$frontendUrl = 'http://127.0.0.1:3003'
$snapshotUrl = 'http://127.0.0.1:3003/?snapshotDemo=1&tab=quarter'

Write-Host 'Starting bizPA snapshot lifecycle UI...' -ForegroundColor Cyan

$frontendCommand = "Set-Location '$frontendPath'; `$env:PORT='3003'; npm.cmd start"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand | Out-Null

Write-Host ''
Write-Host 'Snapshot lifecycle UI URL:' -ForegroundColor Green
Write-Host "  $snapshotUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Base frontend URL:' -ForegroundColor Green
Write-Host "  $frontendUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'This launch path uses the local snapshot demo state so the version list, diff review, warnings, and quarter controls can be reviewed without backend setup.' -ForegroundColor Cyan
