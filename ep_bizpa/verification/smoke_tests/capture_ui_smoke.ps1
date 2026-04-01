$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$backendJob = Start-Job -ScriptBlock {
  Set-Location 'C:\Users\edebe\eds\bizPA\backend'
  npm.cmd run dev
}

$frontendJob = Start-Job -ScriptBlock {
  Set-Location 'C:\Users\edebe\eds\bizPA\frontend'
  $env:PORT = '3001'
  npm.cmd start
}

try {
  $frontendReady = $false
  for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 2
    try {
      $frontendResponse = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:3001/?captureDemo=1'
      if ($frontendResponse.StatusCode -eq 200) {
        $frontendReady = $true
        break
      }
    } catch {
    }
  }

  $backendReady = $false
  for ($i = 0; $i -lt 10; $i++) {
    try {
      $backendResponse = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5056/api/health'
      if ($backendResponse.StatusCode -eq 200) {
        $backendReady = $true
        break
      }
    } catch {
      Start-Sleep -Seconds 2
    }
  }

  if (-not $frontendReady) {
    throw 'Frontend did not become ready on http://127.0.0.1:3001/?captureDemo=1'
  }

  $screenshotPath = 'C:\Users\edebe\eds\workstream\verification\20260311_161949_bizpa_monetary_capture_ui_screenshot.png'
  $chrome = Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' '--new-window --window-size=1440,1400 http://127.0.0.1:3001/?captureDemo=1' -PassThru
  Start-Sleep -Seconds 8
  $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
  $bitmap.Save($screenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bitmap.Dispose()
  if ($chrome -and -not $chrome.HasExited) {
    Stop-Process -Id $chrome.Id -Force -ErrorAction SilentlyContinue
  }

  "FRONTEND_STATUS=$($frontendResponse.StatusCode)"
  "BACKEND_STATUS=$(if ($backendReady) { $backendResponse.StatusCode } else { 'not_ready' })"
  "SCREENSHOT=$screenshotPath"
  'BACKEND_LOG_START'
  Receive-Job $backendJob -Keep -ErrorAction SilentlyContinue 2>&1
  'BACKEND_LOG_END'
  'FRONTEND_LOG_START'
  Receive-Job $frontendJob -Keep -ErrorAction SilentlyContinue 2>&1
  'FRONTEND_LOG_END'
} finally {
  Stop-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue | Out-Null
  Remove-Job $backendJob, $frontendJob -Force -ErrorAction SilentlyContinue | Out-Null
}
