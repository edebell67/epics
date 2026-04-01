$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class WindowCaptureNative {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$frontendUrl = 'http://127.0.0.1:3001/?commandCentreDemo=1&tab=control'
$backendUrl = 'http://127.0.0.1:5056/api/health'
$screenshotPath = 'C:\Users\edebe\eds\workstream\verification\20260311_203500_bizpa_control_centre_auto_commit.png'
$chromeProfilePath = 'C:\Users\edebe\eds\workstream\verification\chrome_capture_profile_home'

New-Item -ItemType Directory -Force -Path $chromeProfilePath | Out-Null

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
  $frontendResponse = $null
  $frontendReady = $false
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
      $frontendResponse = Invoke-WebRequest -UseBasicParsing $frontendUrl
      if ($frontendResponse.StatusCode -eq 200) {
        $frontendReady = $true
        break
      }
    } catch {
    }
  }

  $backendResponse = $null
  $backendReady = $false
  for ($i = 0; $i -lt 15; $i++) {
    try {
      $backendResponse = Invoke-WebRequest -UseBasicParsing $backendUrl
      if ($backendResponse.StatusCode -eq 200) {
        $backendReady = $true
        break
      }
    } catch {
      Start-Sleep -Seconds 2
    }
  }

  if (-not $frontendReady) {
    throw "Frontend did not become ready on $frontendUrl"
  }

  $chromeArgs = @(
    "--user-data-dir=$chromeProfilePath",
    '--new-window',
    '--window-size=1500,1400',
    '--no-first-run',
    '--disable-session-crashed-bubble',
    '--disable-infobars',
    '--disable-breakpad',
    '--disable-crash-reporter',
    '--noerrdialogs',
    "--app=$frontendUrl"
  )
  $chrome = Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList $chromeArgs -PassThru
  Start-Sleep -Seconds 8
  $chromeWindow = $null
  for ($i = 0; $i -lt 10; $i++) {
    $chromeWindow = Get-Process chrome -ErrorAction SilentlyContinue |
      Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*bizPA Dashboard*' } |
      Select-Object -First 1
    if ($chromeWindow) {
      break
    }
    Start-Sleep -Seconds 1
  }
  if ($chromeWindow) {
    [WindowCaptureNative]::ShowWindow($chromeWindow.MainWindowHandle, 3) | Out-Null
    [WindowCaptureNative]::SetForegroundWindow($chromeWindow.MainWindowHandle) | Out-Null
    Start-Sleep -Seconds 1
  }
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

  "COMMAND_CENTRE_URL=$frontendUrl"
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
