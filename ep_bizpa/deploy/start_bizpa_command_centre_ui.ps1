$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $repoRoot 'backend'
$frontendPath = Join-Path $repoRoot 'frontend'
$backendUrl = 'http://127.0.0.1:5056/api/health'
$frontendUrl = 'http://127.0.0.1:3001'
$commandCentreUrl = 'http://127.0.0.1:3001/?commandCentreDemo=1&tab=control'

Write-Host 'Starting bizPA homepage command centre services...' -ForegroundColor Cyan

$backendCommand = "Set-Location '$backendPath'; npm.cmd run dev"
$frontendCommand = "Set-Location '$frontendPath'; `$env:PORT='3001'; npm.cmd start"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCommand | Out-Null
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand | Out-Null

Write-Host ''
Write-Host 'Control centre URL:' -ForegroundColor Green
Write-Host "  $commandCentreUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Base frontend URL:' -ForegroundColor Green
Write-Host "  $frontendUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Backend health URL:' -ForegroundColor Green
Write-Host "  $backendUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Open the control centre first. Use the Capture tab to confirm the persistent auto-commit banner and mode badge.' -ForegroundColor Cyan
