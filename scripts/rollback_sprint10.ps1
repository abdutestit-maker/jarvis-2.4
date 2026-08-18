param(
    [string]$TargetRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$KeepDemoApp
)

$ErrorActionPreference = 'Stop'
$Workspace = [System.IO.Path]::GetFullPath($TargetRoot).TrimEnd('\')
$SourceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$BackupRoot = Join-Path $SourceRoot 'artifacts\sprint10\original'
$Actions = [System.Collections.Generic.List[object]]::new()

function Assert-InWorkspace([string]$Path) {
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if ($resolved -ne $Workspace -and -not $resolved.StartsWith($Workspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Rollback path escaped target workspace: $resolved"
    }
    return $resolved
}

function Restore-SprintFile([string]$RelativePath) {
    $source = Join-Path $BackupRoot $RelativePath
    $target = Assert-InWorkspace (Join-Path $Workspace $RelativePath)
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing Sprint 10 backup: $source"
    }
    $parent = Split-Path -Parent $target
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
    $Actions.Add([pscustomobject]@{ action = 'restore'; path = $target })
}

function Remove-SprintFile([string]$RelativePath) {
    $target = Assert-InWorkspace (Join-Path $Workspace $RelativePath)
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
        $Actions.Add([pscustomobject]@{ action = 'remove'; path = $target })
    }
}

@(
    'core\capability_engine.py',
    'core\platform\__init__.py',
    'core\platform\browser.py',
    'core\platform\windows.py',
    'pyproject.toml',
    'requirements.txt'
) | ForEach-Object { Restore-SprintFile $_ }

@(
    'core\operator\__init__.py',
    'core\operator\adapters.py',
    'core\operator\knowledge.py',
    'core\operator\mission.py',
    'core\operator\reference.py',
    'core\operator\semantic.py',
    'core\operator\session.py',
    'core\operator\software.py',
    'core\operator\windows.py',
    'tests\test_sprint10_adapters.py',
    'tests\test_sprint10_browser.py',
    'tests\test_sprint10_mission.py',
    'tests\test_sprint10_reference.py',
    'tests\test_sprint10_software.py',
    'tests\test_sprint10_windows.py',
    'scripts\sprint10_live_demo.py',
    'scripts\rollback_sprint10.ps1',
    'docs\sprints\SPRINT10_SPEC.md',
    'tasks\plan.md',
    'tasks\todo.md',
    'data\app_knowledge\Notepad.json',
    'data\capabilities\operator_Notepad.json',
    'data\capabilities\episodes\c610b6f38ab0488886b33a53d39e2c0a.json',
    'data\capabilities\episodes\24e13fdcb04740ccb4da39075afc1942.json'
) | ForEach-Object { Remove-SprintFile $_ }

if (-not $KeepDemoApp -and $Workspace -eq $SourceRoot) {
    Get-Process -Name 'notepad++' -ErrorAction SilentlyContinue | ForEach-Object {
        [void]$_.CloseMainWindow()
    }
    Start-Sleep -Seconds 2
    winget uninstall --id Notepad++.Notepad++ --exact --source winget `
        --disable-interactivity --silent | Out-Null
    $Actions.Add([pscustomobject]@{ action = 'uninstall'; path = 'Notepad++.Notepad++' })

    $demoConfig = [System.IO.Path]::GetFullPath((Join-Path $env:APPDATA 'Notepad++'))
    $expectedConfig = [System.IO.Path]::GetFullPath("$env:APPDATA\Notepad++")
    if ($demoConfig -eq $expectedConfig -and (Test-Path -LiteralPath $demoConfig)) {
        Remove-Item -LiteralPath $demoConfig -Recurse -Force
        $Actions.Add([pscustomobject]@{ action = 'remove_demo_profile'; path = $demoConfig })
    }
}

$result = [pscustomobject]@{
    rolled_back = $true
    target_root = $Workspace
    kept_demo_app = [bool]$KeepDemoApp
    actions = $Actions
}
$result | ConvertTo-Json -Depth 5
