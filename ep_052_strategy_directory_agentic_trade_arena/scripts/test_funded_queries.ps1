# VERSION HISTORY v1.0.0 · 2026-09-02 · Live external HTTP review of seeded funding, separate query API and fee/retry effects.
$ErrorActionPreference = 'Stop'
$epicRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$appRoot = Join-Path $epicRoot 'lean_delivery/app'
$credentialPath = Join-Path $appRoot 'runtime/review-owner.json'
$env:PYTHONPATH = Join-Path $appRoot 'src'
if (-not (Test-Path -LiteralPath $credentialPath)) {
    python -m lean_exchange.admin create-owner --name 'Local review owner' --output $credentialPath
    if ($LASTEXITCODE -ne 0) { throw 'Owner bootstrap failed' }
}
$owner = Get-Content -Raw -LiteralPath $credentialPath | ConvertFrom-Json
$ownerHeaders = @{Authorization='Bearer ' + $owner.token}
$agent = Invoke-RestMethod 'http://127.0.0.1:8054/v1/owner/agents' -Method Post -Headers $ownerHeaders -ContentType 'application/json' -Body '{"name":"Funded query review (HTTP client, not Hermes)"}'
$auth = @{Authorization='Bearer ' + $agent.token}
$connection = $null
try {
    $connectionBody = @{request_id=[guid]::NewGuid().ToString();purpose='strategy_trading'} | ConvertTo-Json
    $connection = Invoke-RestMethod 'http://127.0.0.1:8054/v1/connections' -Method Post -Headers $auth -ContentType 'application/json' -Body $connectionBody
    $before = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/funds' -Headers $auth
    $config = (Invoke-RestMethod 'http://127.0.0.1:8054/v1/exchange').configuration
    $query = @{request_id=[guid]::NewGuid().ToString();kind='lowest_drawdown';limit=3;revision=0}
    $first = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/queries' -Method Post -Headers $auth -ContentType 'application/json' -Body ($query | ConvertTo-Json)
    $retry = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/queries' -Method Post -Headers $auth -ContentType 'application/json' -Body ($query | ConvertTo-Json)
    if ($first.delivery.delivery_id -ne $retry.delivery.delivery_id) { throw 'Exact retry changed receipt' }
    $afterRetry = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/funds' -Headers $auth
    if ([decimal]$afterRetry.spendable_usd -ne ([decimal]$before.spendable_usd - [decimal]$config.intelligence_fee)) { throw 'Exact retry fee mismatch' }
    $query.revision = 1
    $refreshed = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/queries' -Method Post -Headers $auth -ContentType 'application/json' -Body ($query | ConvertTo-Json)
    $afterRefresh = Invoke-RestMethod 'http://127.0.0.1:8054/participant/v1/me/funds' -Headers $auth
    if ([decimal]$afterRefresh.spendable_usd -ne ([decimal]$before.spendable_usd - 2*[decimal]$config.intelligence_fee)) { throw 'Refreshed result fee mismatch' }
    $recovered = Invoke-RestMethod "http://127.0.0.1:8054/participant/v1/me/queries/$($first.delivery.delivery_id)" -Headers $auth
    if ($recovered.delivery.delivery_id -ne $first.delivery.delivery_id) { throw 'Recovery mismatch' }
    @{status='PASS';seed_usd=$before.seed_usd;after_exact_retry_usd=$afterRetry.spendable_usd;after_refresh_usd=$afterRefresh.spendable_usd;fee_usd=$config.intelligence_fee;mode=$first.delivery.mode;strategy_ids=$first.delivery.strategy_ids;receipt=$first.delivery.delivery_id;refreshed_receipt=$refreshed.delivery.delivery_id;movement_count=$afterRefresh.movements.Count} | ConvertTo-Json -Depth 5
} finally {
    if ($connection) { Invoke-RestMethod "http://127.0.0.1:8054/v1/connections/$($connection.id)" -Method Delete -Headers $auth | Out-Null }
    Invoke-RestMethod "http://127.0.0.1:8054/v1/owner/credentials/$($agent.credential_id)" -Method Delete -Headers $ownerHeaders | Out-Null
}
