# VERSION HISTORY v1.0.0 · 2026-09-02 · Prepare isolated review identities or respond as an external HTTP test agent; never claim autonomous Hermes.
param([ValidateSet('prepare','respond')][string]$Stage='prepare', [string]$FeedbackId='')
$ErrorActionPreference = 'Stop'
$epicRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$appRoot = Join-Path $epicRoot 'lean_delivery/app'
$ownerPath = Join-Path $appRoot 'runtime/feedback-review-owner.json'
$agentsPath = Join-Path $appRoot 'runtime/feedback-review-agents.json'
$env:PYTHONPATH = Join-Path $appRoot 'src'
if ($Stage -eq 'prepare') {
    if (-not (Test-Path -LiteralPath $ownerPath)) {
        python -m lean_exchange.admin create-owner --name 'Feedback browser review' --output $ownerPath
        if ($LASTEXITCODE -ne 0) { throw 'Owner bootstrap failed' }
    }
    $owner = Get-Content -Raw -LiteralPath $ownerPath | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath $agentsPath)) {
        $auth = @{Authorization='Bearer ' + $owner.token}
        $agents = @('Review agent A','Review agent B') | ForEach-Object {
            Invoke-RestMethod 'http://127.0.0.1:8054/v1/owner/agents' -Method Post -Headers $auth -ContentType 'application/json' -Body (@{name=$_} | ConvertTo-Json)
        }
        [IO.File]::WriteAllText($agentsPath, ($agents | ConvertTo-Json -Depth 5))
    }
    Write-Output 'Review prepared. Credentials remain in ignored runtime files; do not share them.'
    Write-Output 'Owner UI: http://127.0.0.1:8054/owner'
} else {
    $agents = @(Get-Content -Raw -LiteralPath $agentsPath | ConvertFrom-Json)
    $auth = @{Authorization='Bearer ' + $agents[0].token}
    $inbox = Invoke-RestMethod 'http://127.0.0.1:8054/v1/me/feedback' -Headers $auth
    if (-not $FeedbackId) { $FeedbackId=($inbox.items | Sort-Object cursor -Descending | Select-Object -First 1).id }
    if (-not $FeedbackId) { throw 'Send browser feedback to Review agent A first.' }
    $ack = Invoke-RestMethod "http://127.0.0.1:8054/v1/me/feedback/$FeedbackId/ack" -Method Post -Headers $auth
    $reply = @{request_id=[guid]::NewGuid().ToString();message='Received through the API. This test client has reported HOLD; no trade was executed.'}
    $response = Invoke-RestMethod "http://127.0.0.1:8054/v1/me/feedback/$FeedbackId/responses" -Method Post -Headers $auth -ContentType 'application/json' -Body ($reply | ConvertTo-Json)
    $hold = @{request_id=[guid]::NewGuid().ToString();action='HOLD';explanation='External HTTP acceptance check only.'}
    $decision = Invoke-RestMethod 'http://127.0.0.1:8054/v1/me/decisions' -Method Post -Headers $auth -ContentType 'application/json' -Body ($hold | ConvertTo-Json)
    @{status='PASS';feedback_id=$FeedbackId;acknowledged_at=$ack.acknowledged_at;reply_id=$response.id;decision_id=$decision.id;hold_fee_usd=$decision.fee_usd;autonomous_agent=$false} | ConvertTo-Json
}
