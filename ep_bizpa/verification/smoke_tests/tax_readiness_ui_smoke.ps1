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

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

$frontendUrl = 'http://127.0.0.1:3002'
$readinessUrl = 'http://127.0.0.1:3002/?readinessDemo=1&tab=quarter'
$screenshotPath = 'C:\Users\edebe\eds\workstream\verification\20260311_201500_bizpa_tax_readiness_ui.png'
$chromeProfilePath = 'C:\Users\edebe\eds\workstream\verification\chrome_capture_profile_tax_readiness'

New-Item -ItemType Directory -Force -Path $chromeProfilePath | Out-Null

$frontendJob = Start-Job -ScriptBlock {
  Set-Location 'C:\Users\edebe\eds\bizPA\frontend'
  $env:PORT = '3002'
  npm.cmd start
}

try {
  $frontendResponse = $null
  $frontendReady = $false
  for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 2
    try {
      $frontendResponse = Invoke-WebRequest -UseBasicParsing $readinessUrl
      if ($frontendResponse.StatusCode -eq 200) {
        $frontendReady = $true
        break
      }
    } catch {
    }
  }

  if (-not $frontendReady) {
    throw "Frontend did not become ready on $readinessUrl"
  }

  $chromeArgs = @(
    "--user-data-dir=$chromeProfilePath",
    '--new-window',
    '--window-size=1600,1500',
    '--no-first-run',
    '--disable-session-crashed-bubble',
    '--disable-infobars',
    '--disable-breakpad',
    '--disable-crash-reporter',
    '--noerrdialogs',
    "--app=$readinessUrl"
  )
  Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList $chromeArgs | Out-Null

  $chromeWindow = $null
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    $chromeWindow = Get-Process chrome -ErrorAction SilentlyContinue |
      ForEach-Object {
        try {
          if ($_.MainWindowHandle -and ([int64]$_.MainWindowHandle -ne 0)) {
            [pscustomobject]@{
              Process = $_
              StartTime = $_.StartTime
            }
          }
        } catch {
        }
      } |
      Sort-Object StartTime -Descending |
      Select-Object -First 1
    if ($chromeWindow) {
      $chromeWindow = $chromeWindow.Process
      break
    }
  }

  if (-not $chromeWindow) {
    throw 'Chrome readiness window did not expose a main window handle for screenshot capture.'
  }

  [WindowCaptureNative]::ShowWindow($chromeWindow.MainWindowHandle, 3) | Out-Null
  [WindowCaptureNative]::SetForegroundWindow($chromeWindow.MainWindowHandle) | Out-Null
  Start-Sleep -Seconds 1

  $rect = New-Object WindowCaptureNative+RECT
  [WindowCaptureNative]::GetWindowRect($chromeWindow.MainWindowHandle, [ref]$rect) | Out-Null
  $width = [Math]::Max(1, $rect.Right - $rect.Left)
  $height = [Math]::Max(1, $rect.Bottom - $rect.Top)
  $bitmap = New-Object System.Drawing.Bitmap $width, $height
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
  $bitmap.Save($screenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bitmap.Dispose()

  Get-Process chrome -ErrorAction SilentlyContinue |
    Where-Object { $_.StartTime -ge $chromeWindow.StartTime.AddSeconds(-2) } |
    Stop-Process -Force -ErrorAction SilentlyContinue

  "READINESS_URL=$readinessUrl"
  "FRONTEND_STATUS=$($frontendResponse.StatusCode)"
  "SCREENSHOT=$screenshotPath"
  'FRONTEND_LOG_START'
  Receive-Job $frontendJob -Keep -ErrorAction SilentlyContinue 2>&1
  'FRONTEND_LOG_END'
} finally {
  Stop-Job $frontendJob -ErrorAction SilentlyContinue | Out-Null
  Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue | Out-Null
}
