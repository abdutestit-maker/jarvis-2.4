$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:JARVIS_HOME = $Root

& python (Join-Path $Root "scripts\package_local_runtime.py")
if ($LASTEXITCODE -ne 0) {
    throw "Production runtime packaging failed with exit code $LASTEXITCODE"
}

Push-Location (Join-Path $Root "jarvis")
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
    npm run tauri:build
    if ($LASTEXITCODE -ne 0) { throw "tauri build failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

Write-Output "JARVIS build finished. Run .\Start-JARVIS.bat"
