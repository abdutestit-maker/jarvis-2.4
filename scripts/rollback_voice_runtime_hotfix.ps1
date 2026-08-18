$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backupRoot = Join-Path $projectRoot "artifacts\voice_runtime_hotfix\original"
$ttsBackup = Join-Path $backupRoot "core_voice_tts.py"
$testBackup = Join-Path $backupRoot "test_voice_hardening.py"

if (-not (Test-Path -LiteralPath $ttsBackup) -or
    -not (Test-Path -LiteralPath $testBackup)) {
    throw "Voice runtime hotfix backups are missing: $backupRoot"
}

Copy-Item -LiteralPath $ttsBackup `
    -Destination (Join-Path $projectRoot "core\voice\tts.py") -Force
Copy-Item -LiteralPath $testBackup `
    -Destination (Join-Path $projectRoot "tests\test_voice_hardening.py") -Force

$runtimeRoot = Join-Path $projectRoot "data\runtime\piper"
if (Test-Path -LiteralPath $runtimeRoot) {
    $resolvedRuntime = (Resolve-Path -LiteralPath $runtimeRoot).Path
    $resolvedData = (Resolve-Path -LiteralPath (Join-Path $projectRoot "data")).Path
    if (-not $resolvedRuntime.StartsWith($resolvedData + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Runtime path escaped project data directory: $resolvedRuntime"
    }
    Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
}

$smokeScript = Join-Path $projectRoot "scripts\voice_runtime_smoke.py"
if (Test-Path -LiteralPath $smokeScript) {
    Remove-Item -LiteralPath $smokeScript -Force
}

Write-Host "Voice runtime hotfix rolled back."
Write-Host "Restored: core\voice\tts.py"
Write-Host "Restored: tests\test_voice_hardening.py"
Write-Host "Removed: data\runtime\piper"
Write-Host "Removed: scripts\voice_runtime_smoke.py"
