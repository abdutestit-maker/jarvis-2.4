param(
    [string]$ManifestPath = "artifacts/sprint15/baseline_manifest.json",
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$manifestFile = Join-Path $project $ManifestPath
if (-not (Test-Path -LiteralPath $manifestFile)) { throw "Rollback manifest not found: $manifestFile" }
$manifest = Get-Content -Raw -LiteralPath $manifestFile | ConvertFrom-Json
$snapshot = Join-Path (Split-Path -Parent $manifestFile) 'original'
$backup = Join-Path $project ("artifacts/sprint15/rollback_backup/" + (Get-Date -Format 'yyyyMMdd_HHmmss'))

function Assert-SafeTarget([string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    $root = $project.TrimEnd('\') + '\'
    if (-not $full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe rollback target: $full"
    }
}

foreach ($entry in @($manifest.files)) {
    $relative = [string]$entry.path
    $target = Join-Path $project $relative
    Assert-SafeTarget $target
    if ($entry.kind -eq 'existing') {
        $saved = Join-Path $snapshot $relative
        if (-not (Test-Path -LiteralPath $saved)) { throw "Snapshot file missing: $saved" }
        if (-not $DryRun) {
            $backupPath = Join-Path $backup $relative
            New-Item -ItemType Directory -Force -Path (Split-Path $backupPath) | Out-Null
            if (Test-Path -LiteralPath $target) { Copy-Item -LiteralPath $target -Destination $backupPath -Force }
            New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
            Copy-Item -LiteralPath $saved -Destination $target -Force
        }
        Write-Output ("RESTORE " + $relative)
    } else {
        if (-not $DryRun -and (Test-Path -LiteralPath $target)) {
            $resolved = (Resolve-Path -LiteralPath $target).Path
            Assert-SafeTarget $resolved
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
        Write-Output ("REMOVE " + $relative)
    }
}
if (-not $DryRun) { Write-Output ("Rollback complete; backup=" + $backup) }
