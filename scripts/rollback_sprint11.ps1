[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Workspace = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($Workspace).TrimEnd([IO.Path]::DirectorySeparatorChar)
$rootPrefix = $root + [IO.Path]::DirectorySeparatorChar

function Resolve-WorkspacePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $candidate = [IO.Path]::GetFullPath((Join-Path $root $RelativePath))
    if (-not $candidate.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Rollback target escaped workspace: $candidate"
    }
    return $candidate
}

$backupRoot = Resolve-WorkspacePath 'artifacts\sprint11\original'
$restoreMap = [ordered]@{
    'core\agent.py' = 'core\agent.py'
    'core\orchestrator.py' = 'core\orchestrator.py'
    'core\shadow\backlog.py' = 'core\shadow\backlog.py'
    'core\shadow\engine.py' = 'core\shadow\engine.py'
}

$restored = @()
foreach ($relative in $restoreMap.Keys) {
    $source = [IO.Path]::GetFullPath((Join-Path $backupRoot $restoreMap[$relative]))
    $target = Resolve-WorkspacePath $relative
    if (-not $source.StartsWith(($backupRoot + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Backup source escaped backup root: $source"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing Sprint 11 backup: $source"
    }
    if ($PSCmdlet.ShouldProcess($target, 'restore Sprint 11 baseline')) {
        $parent = Split-Path -Parent $target
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
        $expected = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash
        if ($actual -ne $expected) {
            throw "Restored hash mismatch: $relative"
        }
        $restored += $relative
    }
}

$newPaths = @(
    'core\living',
    'tests\test_sprint11_context.py',
    'tests\test_sprint11_workflow.py',
    'tests\test_sprint11_proactive.py',
    'tests\test_sprint11_resources.py',
    'tests\test_sprint11_service.py',
    'scripts\sprint11_live_demo.py',
    'docs\sprints\SPRINT11_SPEC.md',
    'tasks\sprint11_plan.md',
    'tasks\sprint11_todo.md',
    'data\living'
)

$removed = @()
foreach ($relative in $newPaths) {
    $target = Resolve-WorkspacePath $relative
    if (-not (Test-Path -LiteralPath $target)) {
        continue
    }
    if ($PSCmdlet.ShouldProcess($target, 'remove Sprint 11 addition')) {
        $item = Get-Item -LiteralPath $target -Force
        if ($item.PSIsContainer) {
            # The absolute path was checked against the workspace before recursion.
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        else {
            Remove-Item -LiteralPath $target -Force
        }
        $removed += $relative
    }
}

[ordered]@{
    sprint = 11
    workspace = $root
    restored = $restored
    removed = $removed
    voice_hotfix_preserved = $true
    sprint10_preserved = $true
    verified = (-not $WhatIfPreference)
} | ConvertTo-Json -Depth 4
