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
    $BackupRoot = Join-Path $project "artifacts\sprint14\original"
}
$backup = [System.IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $backup -PathType Container)) {
    throw "Sprint 14 backup does not exist: $backup"
}

$restore = @(
    "core\cognitive\models.py",
    "core\cognitive\orchestrator.py",
    "core\cognitive\state.py"
)
$added = @(
    "core\metacognition\__init__.py",
    "core\metacognition\audit.py",
    "core\metacognition\calibration.py",
    "core\metacognition\correction.py",
    "core\metacognition\engine.py",
    "core\metacognition\expectation.py",
    "core\metacognition\failures.py",
    "core\metacognition\freshness.py",
    "core\metacognition\models.py",
    "core\metacognition\store.py",
    "docs\sprints\SPRINT14_SPEC.md",
    "scripts\sprint14_live_demo.py",
    "tests\test_sprint14_adversarial.py",
    "tests\test_sprint14_correction.py",
    "tests\test_sprint14_epistemic.py",
    "tests\test_sprint14_integration.py",
    "tests\test_sprint14_knowledge.py",
    "tests\test_sprint14_live_demo.py",
    "scripts\rollback_sprint14.ps1"
)

function Resolve-Within([string]$Root, [string]$RelativePath) {
    $candidate = [System.IO.Path]::GetFullPath((Join-Path $Root $RelativePath))
    if (-not $candidate.StartsWith($Root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes expected root: $RelativePath"
    }
    return $candidate
}

$restored = @()
foreach ($relative in $restore) {
    $source = Resolve-Within $backup $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing original: $source"
    }
    $target = Resolve-Within $project $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
    $restored += $relative
}

$removed = @()
foreach ($relative in $added) {
    $target = Resolve-Within $project $relative
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
        $removed += $relative
    }
}

$cache = Resolve-Within $project "core\metacognition\__pycache__"
if (Test-Path -LiteralPath $cache -PathType Container) {
    Remove-Item -LiteralPath $cache -Recurse -Force
}
$package = Resolve-Within $project "core\metacognition"
if ((Test-Path -LiteralPath $package -PathType Container) -and
    -not (Get-ChildItem -LiteralPath $package -Force | Select-Object -First 1)) {
    Remove-Item -LiteralPath $package -Force
}

[ordered]@{
    success = $true
    project_root = $project
    backup_root = $backup
    restored = $restored
    removed = $removed
} | ConvertTo-Json -Depth 5
