param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$BackupRoot = ""
)

$ErrorActionPreference = "Stop"
$project = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $project -PathType Container)) {
    throw "Project root does not exist: $project"
}
if (-not $BackupRoot) {
    $BackupRoot = Join-Path $project "artifacts\sprint12\original"
}
$backup = [System.IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $backup -PathType Container)) {
    throw "Sprint 12 backup does not exist: $backup"
}

$restore = @(
    "core\agent.py",
    "core\orchestrator.py",
    "core\living\service.py",
    "core\voice\greeting.py",
    "core\ws_server.py",
    "core\memory\__init__.py",
    "persona\system_prompt.py"
)
$added = @(
    "core\personality\__init__.py",
    "core\personality\communication.py",
    "core\personality\engine.py",
    "core\personality\humor.py",
    "core\personality\models.py",
    "core\memory\relationship\__init__.py",
    "core\memory\relationship\hierarchy.py",
    "core\memory\relationship\learning.py",
    "core\memory\relationship\models.py",
    "core\memory\relationship\store.py",
    "persona\identity.json",
    "persona\personality.json",
    "tests\test_sprint12_personality.py",
    "tests\test_sprint12_relationship.py",
    "tests\test_sprint12_integration.py",
    "scripts\sprint12_live_demo.py",
    "docs\sprints\SPRINT12_SPEC.md",
    "tasks\sprint12_plan.md",
    "tasks\sprint12_todo.md"
)

function Resolve-ProjectFile([string]$RelativePath) {
    $candidate = [System.IO.Path]::GetFullPath((Join-Path $project $RelativePath))
    if (-not $candidate.StartsWith($project + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes project root: $RelativePath"
    }
    return $candidate
}

$restored = @()
foreach ($relative in $restore) {
    $source = [System.IO.Path]::GetFullPath((Join-Path $backup $relative))
    if (-not $source.StartsWith($backup + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Backup path escapes backup root: $relative"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing original: $source"
    }
    $target = Resolve-ProjectFile $relative
    $parent = Split-Path -Parent $target
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
    $restored += $relative
}

$removed = @()
foreach ($relative in $added) {
    $target = Resolve-ProjectFile $relative
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
        $removed += $relative
    }
}

# Only empty Sprint 12 package directories are removed; no recursive deletion.
foreach ($relative in @("core\memory\relationship", "core\personality")) {
    $directory = [System.IO.Path]::GetFullPath((Join-Path $project $relative))
    if ($directory.StartsWith($project + '\', [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $directory -PathType Container) -and
        -not (Get-ChildItem -LiteralPath $directory -Force | Select-Object -First 1)) {
        Remove-Item -LiteralPath $directory -Force
    }
}

[ordered]@{
    success = $true
    project_root = $project
    backup_root = $backup
    restored = $restored
    removed = $removed
} | ConvertTo-Json -Depth 4
