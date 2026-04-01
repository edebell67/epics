param(
  [int]$Port = 4173
)

$ErrorActionPreference = "Stop"

$EpicRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $EpicRoot "solution\frontend"
$VerificationDir = Join-Path $EpicRoot "verification"
$StartScript = Join-Path $EpicRoot "start_evidence_match_ui.ps1"
$ScreenshotPath = Join-Path $VerificationDir "20260326_voice_confirmation_chip.png"
$VoiceCommand = "Category: Travel"
$EncodedVoice = [System.Uri]::EscapeDataString($VoiceCommand)
$Url = "http://127.0.0.1:$Port/?context=inbox&voice=$EncodedVoice"
$PayloadPath = Join-Path $FrontendDir "data\evidence-match-demo.json"
$RenderScript = Join-Path $FrontendDir "render_voice_ui_screenshot.py"

New-Item -ItemType Directory -Force -Path $VerificationDir | Out-Null

& $StartScript -Port $Port -VoiceCommand $VoiceCommand -NoOpen | Out-Host

$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    if ($response.StatusCode -eq 200) {
      $healthy = $true
      break
    }
  } catch {
    Start-Sleep -Milliseconds 500
  }
}

if (-not $healthy) {
  throw "Evidence UI did not return HTTP 200 on $Url"
}

python $RenderScript $PayloadPath $ScreenshotPath | Out-Host

if (-not (Test-Path $ScreenshotPath)) {
  throw "Screenshot capture failed: $ScreenshotPath"
}

Write-Host "FRONTEND_STATUS=200"
Write-Host "SCREENSHOT=$ScreenshotPath"
