# VERSION HISTORY v1.0.0 · 2026-09-02 · Start an isolated review instance without publishing fixture prices into the main app.
param([int]$Port=8056)
$ErrorActionPreference = 'Stop'
$epicRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { throw "Port $Port already occupied; existing service left untouched." }
$env:PYTHONPATH = Join-Path $epicRoot 'lean_delivery/app/src'
$runDir = Join-Path $epicRoot ('evidence/trading/review_' + (Get-Date -Format yyyyMMdd_HHmmss_fff))
$script = Join-Path $PSScriptRoot 'trade_review.py'
python $script prepare --run-dir $runDir --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Review preparation failed' }
$process = Start-Process -FilePath (Get-Command python).Source -ArgumentList @(('"'+$script+'"'),'run','--run-dir',('"'+$runDir+'"'),'--port',$Port) -WorkingDirectory $epicRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runDir 'server.stdout.log') -RedirectStandardError (Join-Path $runDir 'server.stderr.log')
Write-Output "Isolated review PID $($process.Id): http://127.0.0.1:$Port/docs"
Write-Output "Run directory: $runDir"
Write-Output 'Quotes are explicitly labelled acceptance fixtures, not live valuations. Main8054 data is unchanged.'
