$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$uiUrl = 'http://localhost:19011/business_entity_deep_dive_preview.html?entity=invoice'
$apiUrl = 'http://127.0.0.1:5056/api/v1/business-events/entity-view/invoice/entity-invoice-001'

Write-Host 'Starting bizPA entity deep-dive UI...' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Entity deep-dive URL:' -ForegroundColor Green
Write-Host "  $uiUrl" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Backend entity detail route pattern:' -ForegroundColor Green
Write-Host "  $apiUrl" -ForegroundColor Yellow
Write-Host ''

Write-Host 'Serving preview locally. Press Ctrl+C to stop.' -ForegroundColor Cyan
Set-Location $repoRoot
python -m http.server 19011 --directory $repoRoot
