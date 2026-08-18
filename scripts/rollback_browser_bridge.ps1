[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$DryRun,
    [switch]$Force,
    [string]$WorkspaceRoot = "E:\\jarvis-project"
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$manifestPath = Join-Path $root "artifacts\\browser_bridge\\baseline_manifest.json"
$snapshotRoot = Join-Path $root "artifacts\\browser_bridge\\original"

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Browser Bridge manifest not found: $manifestPath"
}
if (-not (Test-Path -LiteralPath $snapshotRoot -PathType Container)) {
    throw "Browser Bridge snapshot not found: $snapshotRoot"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($entry in @($manifest.files)) {
    $target = Join-Path $root $entry.path
    $resolved = [System.IO.Path]::GetFullPath($target)
    if (-not $resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Manifest target escapes workspace: $resolved"
    }
    if ($entry.kind -eq "new") {
        if (Test-Path -LiteralPath $resolved) {
            if ($DryRun) { Write-Host "[dry-run] remove $resolved" }
            elseif ($PSCmdlet.ShouldProcess($resolved, "Remove Browser Bridge file")) { Remove-Item -LiteralPath $resolved -Force }
        }
        continue
    }
    $snapshot = Join-Path $snapshotRoot $entry.path
    if (-not (Test-Path -LiteralPath $snapshot -PathType Leaf)) { throw "Snapshot missing: $snapshot" }
    if ((Test-Path -LiteralPath $resolved) -and -not $Force -and -not $DryRun) {
        $currentHash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($currentHash -ne $entry.sha256) { throw "Refusing to overwrite modified file without -Force: $resolved" }
    }
    if ($DryRun) {
        $current = if (Test-Path -LiteralPath $resolved) { (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() } else { "missing" }
        $state = if ($current -eq $entry.sha256) { "unchanged" } else { "modified" }
        Write-Host "[dry-run] restore $resolved ($state)"
    }
    elseif ($PSCmdlet.ShouldProcess($resolved, "Restore Browser Bridge baseline")) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolved) | Out-Null
        Copy-Item -LiteralPath $snapshot -Destination $resolved -Force
    }
}

if ($DryRun) { Write-Host "Browser Bridge rollback dry-run complete." }
else { Write-Host "Browser Bridge rollback complete." }
