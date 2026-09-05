# VERSION HISTORY v1.0.0 · 2026-09-02 · User-testable owner/agent HTTP access with explicit local test connection and revocation cleanup.
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
$ownerHeaders = @{ Authorization='Bearer ' + $owner.token }
$agent = Invoke-RestMethod 'http://127.0.0.1:8054/v1/owner/agents' -Method Post -Headers $ownerHeaders -ContentType 'application/json' -Body '{"name":"API review client (not autonomous Hermes)"}'
$agentHeaders = @{ Authorization='Bearer ' + $agent.token }
$connection = $null
try {
    $body = @{ request_id=[guid]::NewGuid().ToString(); purpose='strategy_trading' } | ConvertTo-Json
    $connection = Invoke-RestMethod 'http://127.0.0.1:8054/v1/connections' -Method Post -Headers $agentHeaders -ContentType 'application/json' -Body $body
    $heartbeat = Invoke-RestMethod "http://127.0.0.1:8054/v1/connections/$($connection.id)/heartbeat" -Method Post -Headers $agentHeaders
    $arena = Invoke-RestMethod 'http://127.0.0.1:8054/v1/arena/connections' -Headers $ownerHeaders
    if (-not ($arena.items | Where-Object agent_id -eq $agent.agent_id)) { throw 'Connected agent missing from Arena API' }
    $activity = Invoke-RestMethod 'http://127.0.0.1:8054/v1/me/activity' -Headers $agentHeaders
    @{status='PASS'; agent_id=$agent.agent_id; connection_id=$connection.id; active=$heartbeat.active; activity_count=$activity.items.Count; agent_runtime='HTTP test client only'} | ConvertTo-Json
} finally {
    if ($connection) { Invoke-RestMethod "http://127.0.0.1:8054/v1/connections/$($connection.id)" -Method Delete -Headers $agentHeaders | Out-Null }
    Invoke-RestMethod "http://127.0.0.1:8054/v1/owner/credentials/$($agent.credential_id)" -Method Delete -Headers $ownerHeaders | Out-Null
}
try {
    Invoke-RestMethod 'http://127.0.0.1:8054/v1/me' -Headers $agentHeaders | Out-Null
    throw 'Revoked credential unexpectedly accepted'
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
    Write-Output 'PASS: revoked test credential rejected (401).'
}
