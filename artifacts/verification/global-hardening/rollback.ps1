param(
    [string]$Workspace = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
} else {
    $Workspace = (Resolve-Path -LiteralPath $Workspace).Path
}

$baseline = "39bbd090e60e4d5102245f602cbe0f4304f02b71"
$tracked = @(
    "core/actions/app_control.py",
    "core/actions/media.py",
    "core/agent.py",
    "core/orchestrator.py",
    "core/router/intent_router.py",
    "core/verifier.py",
    "scripts/_live_probe.py",
    "tests/test_audit_fixes.py",
    "tests/test_conversation_latency.py",
    "tests/test_media_fast_path.py"
)
$new = @(
    "core/router/route_guard.py",
    "tests/test_conversation_fast_path.py",
    "tests/test_live_probe_harness.py",
    "tests/test_route_guard.py"
)

& git -C $Workspace restore --source $baseline --worktree --staged -- $tracked
if ($LASTEXITCODE -ne 0) { throw "Failed restoring tracked hardening files from $baseline" }

foreach ($file in $new) {
    $absolute = Join-Path $Workspace $file
    if (Test-Path -LiteralPath $absolute -PathType Leaf) {
        Remove-Item -LiteralPath $absolute -Force
    }
}

Write-Output "Restored global hardening source/test files to $baseline. Frontend, model, voice and unrelated artifacts were not touched."
