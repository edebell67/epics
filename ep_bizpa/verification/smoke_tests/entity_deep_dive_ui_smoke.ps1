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

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendUrl = 'http://127.0.0.1:19011/business_entity_deep_dive_preview.html?entity=invoice'
$screenshotPath = 'C:\Users\edebe\eds\workstream\verification\20260311_220500_bizpa_entity_deep_dive_invoice.png'
$chromeProfilePath = 'C:\Users\edebe\eds\workstream\verification\chrome_capture_profile_entity_deep_dive'

New-Item -ItemType Directory -Force -Path $chromeProfilePath | Out-Null

$frontendJob = Start-Job -ScriptBlock {
  Set-Location 'C:\Users\edebe\eds\bizPA'
  python -m http.server 19011 --directory .
}

try {
  $frontendResponse = $null
  $frontendReady = $false
  for ($i = 0; $i -lt 20; $i++) {
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

  if (-not $frontendReady) {
    throw "Frontend did not become ready on $frontendUrl"
  }

  $chromeArgs = @(
    "--user-data-dir=$chromeProfilePath",
    '--new-window',
    '--window-size=1520,1440',
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
      Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*bizPA Entity Deep Dive*' } |
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

  "ENTITY_DEEP_DIVE_URL=$frontendUrl"
  "FRONTEND_STATUS=$($frontendResponse.StatusCode)"
  "SCREENSHOT=$screenshotPath"
  'FRONTEND_LOG_START'
  Receive-Job $frontendJob -Keep -ErrorAction SilentlyContinue 2>&1
  'FRONTEND_LOG_END'
} finally {
  Stop-Job $frontendJob -ErrorAction SilentlyContinue | Out-Null
  Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue | Out-Null
}
