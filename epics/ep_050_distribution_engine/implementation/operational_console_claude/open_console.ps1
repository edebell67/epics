# epics/ep_050_distribution_engine/implementation/operational_console_claude/open_console.ps1
# EP050 Operational Console v2 — readiness poll then browser launch.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial readiness-poll launcher, hardened per the Gemini console launcher lesson
#                        (persistent server window; poll HTTP 200 before opening the browser).

param(
    [int]$Port = 8060,
    [int]$TimeoutSeconds = 20
)

$url = "http://127.0.0.1:$Port/api/status"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    Write-Host "EP050 Operational Console v2 did not become ready on $url within $TimeoutSeconds seconds."
    Write-Host "Check the server window for errors before retrying."
    exit 1
}

Write-Host "EP050 Operational Console v2 is ready at http://127.0.0.1:$Port/"
Start-Process "http://127.0.0.1:$Port/"
