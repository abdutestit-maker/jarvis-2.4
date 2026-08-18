param(
    [string]$ManifestPath = "artifacts/archive/hardening_last_verified/manifest.json",
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$manifestFile = Join-Path $project $ManifestPath
if (-not (Test-Path -LiteralPath $manifestFile)) { throw "Rollback manifest not found: $manifestFile" }
$manifest = Get-Content -Raw -LiteralPath $manifestFile | ConvertFrom-Json
$manifestDir = Split-Path -Parent $manifestFile
$backup = Join-Path $project ("artifacts/archive/hardening_rollback_backup/" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
foreach ($entry in @($manifest.files)) {
    $relative = [string]$entry.path
    $source = Join-Path $project $relative
    $saved = Join-Path $manifestDir ("files\" + $relative)
    if (-not (Test-Path -LiteralPath $saved)) { throw "Snapshot file missing: $saved" }
    $resolved = (Resolve-Path $source -ErrorAction SilentlyContinue).Path
    if ($resolved -and $resolved -notlike "$project*") { throw "Unsafe rollback target: $resolved" }
    if (-not $DryRun) {
        $backupPath = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupPath) | Out-Null
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $backupPath -Force }
        New-Item -ItemType Directory -Force -Path (Split-Path $source) | Out-Null
        Copy-Item -LiteralPath $saved -Destination $source -Force
    }
    Write-Output ("RESTORE " + $relative)
}
if (-not $DryRun) { Write-Output "Rollback restored the last verified hardening snapshot; backup=$backup" }
