# VERSION HISTORY v1.0.0 · 2026-09-02 · User-runnable provider smoke test; no real intelligence, trading or fee charged.
$ErrorActionPreference = 'Stop'
$epicRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$keyPath = Join-Path $epicRoot 'lean_delivery/app/runtime/intelligence.key'
$headers = @{
    Authorization = 'Bearer ' + [IO.File]::ReadAllText($keyPath).Trim()
    'X-EP052-Agent-ID' = [guid]::NewGuid().ToString()
}
$request = @{ request_id=[guid]::NewGuid().ToString(); kind='lowest_drawdown'; limit=3; revision=0 }
$body = $request | ConvertTo-Json
$first = Invoke-RestMethod 'http://127.0.0.1:8055/v1/queries' -Method Post -Headers $headers -ContentType 'application/json' -Body $body
$retry = Invoke-RestMethod 'http://127.0.0.1:8055/v1/queries' -Method Post -Headers $headers -ContentType 'application/json' -Body $body
if ($first.delivery_id -ne $retry.delivery_id) { throw 'Exact retry returned a different delivery' }
$request.revision = 1
$refresh = Invoke-RestMethod 'http://127.0.0.1:8055/v1/queries' -Method Post -Headers $headers -ContentType 'application/json' -Body ($request | ConvertTo-Json)
if ($first.delivery_id -eq $refresh.delivery_id) { throw 'Refresh reused the previous receipt' }
$recovered = Invoke-RestMethod "http://127.0.0.1:8055/v1/deliveries/$($first.delivery_id)" -Headers $headers
if ($recovered.delivery_id -ne $first.delivery_id) { throw 'Receipt recovery failed' }
$result = @{status='PASS'; mode=$first.mode; selected_strategies=$first.strategy_ids; receipt=$first.delivery_id; refreshed_receipt=$refresh.delivery_id; exact_retry='same receipt'; fee='Not charged by provider; participant charging not implemented yet'}
$result | ConvertTo-Json -Depth 5
