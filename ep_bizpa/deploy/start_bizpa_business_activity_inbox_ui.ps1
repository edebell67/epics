$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$uiUrl = 'http://localhost:19009/business_activity_inbox_preview.html'
$apiUrl = 'http://127.0.0.1:5055/api/v1'

Write-Host 'Starting bizPA business activity inbox UI...' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Business activity inbox URL:' -ForegroundColor Green
Write-Host "  $uiUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Configured local API base:' -ForegroundColor Green
Write-Host "  $apiUrl" -ForegroundColor Yellow
Write-Host ''

Write-Host 'Serving preview locally. Press Ctrl+C to stop.' -ForegroundColor Cyan
Set-Location $repoRoot
python -m http.server 19009 --directory $repoRoot
