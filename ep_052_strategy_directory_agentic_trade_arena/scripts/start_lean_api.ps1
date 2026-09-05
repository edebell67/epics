# VERSION HISTORY v1.0.0 · 2026-09-02 · Start loopback APIs with separate private provider credential and per-run logs.
$ErrorActionPreference = 'Stop'
$epicRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$appRoot = Join-Path $epicRoot 'lean_delivery/app'
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$runtimeRoot = Join-Path $appRoot 'runtime'
$logRoot = Join-Path $epicRoot 'evidence/runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot, $logRoot | Out-Null
$secretPath = Join-Path $runtimeRoot 'intelligence.key'
if (-not (Test-Path -LiteralPath $secretPath)) {
    $randomBytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    [IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($randomBytes))
}
$env:EP052_INTELLIGENCE_TOKEN = [IO.File]::ReadAllText($secretPath).Trim()
$env:PYTHONPATH = Join-Path $appRoot 'src'
$runStamp = Get-Date -Format yyyyMMdd_HHmmss
$services = @(
    @{ Port=8054; Module='lean_exchange'; Name='exchange' },
    @{ Port=8055; Module='lean_exchange.simulated_intelligence'; Name='intelligence' }
)
try {
    foreach ($service in $services) {
        $listener = Get-NetTCPConnection -State Listen -LocalPort $service.Port -ErrorAction SilentlyContinue
        if ($listener) {
            Write-Output "Port $($service.Port) already in use; existing service not restarted."
            continue
        }
        $process = Start-Process -FilePath $pythonExe -ArgumentList '-m', $service.Module -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot "$runStamp-$($service.Name).stdout.log") -RedirectStandardError (Join-Path $logRoot "$runStamp-$($service.Name).stderr.log")
        Write-Output "$($service.Name) PID $($process.Id), http://127.0.0.1:$($service.Port)/health"
    }
} finally {
    Remove-Item Env:EP052_INTELLIGENCE_TOKEN
}
Write-Output 'Discovery and working endpoints: http://127.0.0.1:8054/v1/exchange'
