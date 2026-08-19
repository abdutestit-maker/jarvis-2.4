param(
    [string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $Workspace
$baseline = 'f25d72f7df06b5ada2217f4fe18230bd6a796c96'
$tracked = @(
    '.gitignore',
    'README.md',
    'config/models_manifest.json',
    'config/settings.example.json',
    'config/settings.py',
    'core/llm/__init__.py',
    'core/llm/factory.py',
    'core/llm/hardware_profile.py',
    'core/orchestrator.py',
    'jarvis/src-tauri/src/main.rs',
    'jarvis/src-tauri/tauri.conf.json',
    'scripts/run-backend.cmd'
)
$newFiles = @(
    'core/llm/llama_server.py',
    'scripts/package_local_runtime.py',
    'scripts/quality_probe.py',
    'tests/test_llama_server_backend.py',
    'tests/test_quality_probe.py',
    'jarvis/src-tauri/resources/jarvis-runtime/.gitkeep'
)
foreach ($path in $tracked) {
    git restore --source $baseline -- $path
}
foreach ($path in $newFiles) {
    $candidate = Join-Path $Workspace $path
    if (Test-Path -LiteralPath $candidate) {
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        if (-not $resolved.StartsWith($Workspace, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Rollback target escaped workspace: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Force
    }
}
$settingsBackup = Join-Path $Workspace 'data/backups/settings.json.20260819-174809.bak'
$settingsTarget = Join-Path $Workspace 'config/settings.json'
if (Test-Path -LiteralPath $settingsBackup) {
    Copy-Item -LiteralPath $settingsBackup -Destination $settingsTarget -Force
}
Write-Host "Model-runtime changes restored to $baseline."
Write-Host "The local GGUF, installed llama.cpp package, user data, voice and frontend build outputs were left untouched."
