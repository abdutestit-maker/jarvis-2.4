$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:JARVIS_HOME = $Root
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$runtimeTemp = Join-Path $Root "runtime-temp"
New-Item -ItemType Directory -Force -Path $runtimeTemp | Out-Null
$env:JARVIS_RUNTIME_TEMP = $runtimeTemp
$env:TEMP = $runtimeTemp
$env:TMP = $runtimeTemp

$gui = Join-Path $Root "jarvis\src-tauri\target\release\jarvis-frontend.exe"
if (-not (Test-Path -LiteralPath $gui -PathType Leaf)) {
    throw "Production GUI not found: $gui. Run Build-JARVIS.ps1 first. Development/Vite fallback is disabled."
}

Start-Process -FilePath $gui -WorkingDirectory $Root | Out-Null
Write-Output "JARVIS native GUI started: $gui"
