$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backup = Join-Path $root "artifacts/executive_mind_backup_20260818"

function Restore-Backup([string]$relative) {
    $src = Join-Path $backup $relative
    $dst = Join-Path $root $relative
    if (Test-Path -LiteralPath $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
}

# Restore files whose complete working-tree bytes were captured before Sprint 16.
$manifest = Get-Content (Join-Path $backup "manifest.json") -Raw | ConvertFrom-Json
foreach ($entry in $manifest) { Restore-Backup $entry.path }

# These files already contained unrelated work before this sprint. Remove only
# the exact additive fragments owned by Executive Mind instead of resetting git.
$statePath = Join-Path $root "core/state.py"
if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw
    $state = [regex]::Replace($state, '(?m)^\s*executive: Dict\[str, Any\].*\r?\n', '')
    $state = [regex]::Replace($state, '(?m)^\s*executive=\{\},\r?\n', '')
    $state = [regex]::Replace($state, '(?s)\n    # Every state-producing path is self-describing\..*?\n    return state\r?\n', "`r`n")
    Set-Content -LiteralPath $statePath -Value $state -Encoding utf8
}

$verifierPath = Join-Path $root "core/verifier.py"
if (Test-Path $verifierPath) {
    $verifier = Get-Content $verifierPath -Raw
    $verifier = [regex]::Replace($verifier, '(?s)\n\ndef verify_current_time\(.*?\n\ndef default_verify', "`r`n`r`ndef default_verify")
    $verifier = $verifier.Replace('register_verifier("current_time", verify_current_time)' + "`r`n", '')
    $verifier = $verifier.Replace('register_verifier("play_music", verify_play_music)' + "`r`n", '')
    Set-Content -LiteralPath $verifierPath -Value $verifier -Encoding utf8
}

$executorPath = Join-Path $root "core/actions/executor.py"
if (Test-Path $executorPath) {
    $executor = Get-Content $executorPath -Raw
    $executor = $executor.Replace(', "current_time", "play_music"', '')
    Set-Content -LiteralPath $executorPath -Value $executor -Encoding utf8
}

$qwenPath = Join-Path $root "core/llm/local_qwen.py"
if (Test-Path $qwenPath) {
    $qwen = Get-Content $qwenPath -Raw
    $qwen = [regex]::Replace($qwen, '(?s)\n    def runtime_info\(self\).*?\n    def close\(', "`r`n    def close(")
    Set-Content -LiteralPath $qwenPath -Value $qwen -Encoding utf8
}

$memoryInitPath = Join-Path $root "core/memory/__init__.py"
if (Test-Path $memoryInitPath) {
    $memoryInit = Get-Content $memoryInitPath -Raw
    $memoryInit = [regex]::Replace($memoryInit, '(?m)^\s*get_relevant_profile_context,\r?\n', '')
    $memoryInit = [regex]::Replace($memoryInit, '(?m)^\s*"get_relevant_profile_context",\r?\n', '')
    Set-Content -LiteralPath $memoryInitPath -Value $memoryInit -Encoding utf8
}

# Sprint-16-owned paths only.
$owned = @(
    "core/executive", "core/actions/time.py", "core/actions/media.py",
    "tests/test_executive_mind.py", "tests/test_audit_fixes.py",
    "docs/EXECUTIVE_MIND_VERIFICATION.md", "scripts/rollback_executive_mind.ps1"
)
foreach ($relative in $owned) {
    $target = Join-Path $root $relative
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
Write-Output "Executive Mind rollback completed; pre-existing Sprint 8–15 paths were preserved."
