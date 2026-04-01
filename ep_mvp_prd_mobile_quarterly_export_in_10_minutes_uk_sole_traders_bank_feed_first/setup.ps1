[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$directories = @(
    "solution",
    "solution/backend",
    "solution/frontend",
    "verification",
    "verification/artifacts",
    "verification/artifacts/exports"
)

Write-Host "Bootstrapping local MVP quarterly export workspace at $root"

foreach ($relativePath in $directories) {
    $target = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $target)) {
        New-Item -ItemType Directory -Path $target | Out-Null
        Write-Host "Created $relativePath"
    }
    else {
        Write-Host "Exists   $relativePath"
    }
}

$envTemplate = Join-Path $root ".env.example"
$envFile = Join-Path $root ".env"
if ((Test-Path -LiteralPath $envTemplate) -and -not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $envTemplate -Destination $envFile
    Write-Host "Created .env from .env.example"
}
elseif (Test-Path -LiteralPath $envFile) {
    Write-Host "Exists   .env"
}
else {
    Write-Warning ".env.example was not found; skipping .env creation."
}

Write-Host ""
Write-Host "Planned API base path: /api/v1"
Write-Host "Future backend startup hook:"
Write-Host "  - solution/backend should expose the bank-feed, import, and quarterly export services."
Write-Host "Future frontend startup hook:"
Write-Host "  - solution/frontend should host the mobile/web client that calls /api/v1."
