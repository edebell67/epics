param(
  [int]$Port = 4173,
  [string]$VoiceCommand = "",
  [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$EpicRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $EpicRoot "solution\frontend"
$BackendDir = Join-Path $EpicRoot "solution\backend"
$VerificationDir = Join-Path $EpicRoot "verification"
$PidPath = Join-Path $VerificationDir "evidence_ui_server.pid"
$Url = "http://127.0.0.1:$Port/?context=inbox"

if ($VoiceCommand) {
  $encoded = [System.Uri]::EscapeDataString($VoiceCommand)
  $Url = "$Url&voice=$encoded"
}

New-Item -ItemType Directory -Force -Path $VerificationDir | Out-Null

node (Join-Path $BackendDir "generate_evidence_ui_demo.js") | Out-Host

if (Test-Path $PidPath) {
  $existingPid = Get-Content $PidPath -ErrorAction SilentlyContinue
  if ($existingPid) {
    $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($existingProcess) {
      Write-Host "Voice review UI already running at $Url"
      Write-Host "PID=$existingPid"
      if (-not $NoOpen) {
        Start-Process $Url
      }
      return
    }
  }
}

$stdoutPath = Join-Path $VerificationDir "evidence_ui_server.out.log"
$stderrPath = Join-Path $VerificationDir "evidence_ui_server.err.log"
$arguments = @((Join-Path $FrontendDir "server.js"), "$Port")

$process = Start-Process -FilePath "node" `
  -ArgumentList $arguments `
  -WorkingDirectory $FrontendDir `
  -PassThru `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutPath `
  -RedirectStandardError $stderrPath

Set-Content -Path $PidPath -Value $process.Id

Start-Sleep -Seconds 2
Write-Host "Voice review UI started"
Write-Host "URL=$Url"
Write-Host "PID=$($process.Id)"

if (-not $NoOpen) {
  Start-Process $Url
}
