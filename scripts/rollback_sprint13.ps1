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
    $BackupRoot = Join-Path $project "artifacts\sprint13\original"
}
$backup = [System.IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $backup -PathType Container)) {
    throw "Sprint 13 backup does not exist: $backup"
}

$restore = @(
    "config\settings.example.json",
    "config\settings.json",
    "config\settings.py",
    "core\agent.py",
    "core\memory\retrieval.py",
    "core\orchestrator.py",
    "core\personality\models.py",
    "core\research.py",
    "core\router\local_face.py",
    "core\shadow\generator.py",
    "core\voice\wake_word.py",
    "core\ws_server.py",
    "persona\identity.json",
    "persona\persona.md",
    "persona\personality.json",
    "persona\system_prompt.py",
    "scripts\voice_runtime_smoke.py",
    "tests\test_sprint12_integration.py",
    "tests\test_sprint12_personality.py"
)
$added = @(
    "core\cognitive\__init__.py",
    "core\cognitive\addressing.py",
    "core\cognitive\continuity.py",
    "core\cognitive\identity.py",
    "core\cognitive\models.py",
    "core\cognitive\orchestrator.py",
    "core\cognitive\self_model.py",
    "core\cognitive\state.py",
    "docs\sprints\SPRINT13_SPEC.md",
    "scripts\sprint13_live_demo.py",
    "tests\test_sprint13_cognitive_orchestrator.py",
    "tests\test_sprint13_identity_addressing.py",
    "tests\test_sprint13_live_demo.py",
    "tests\test_sprint13_mind_state.py",
    "scripts\rollback_sprint13.ps1"
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

# The only recursive removal is the explicitly resolved Python cache inside
# the newly added cognitive package. Source files were removed individually.
$cache = Resolve-Within $project "core\cognitive\__pycache__"
if (Test-Path -LiteralPath $cache -PathType Container) {
    Remove-Item -LiteralPath $cache -Recurse -Force
}
$package = Resolve-Within $project "core\cognitive"
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
