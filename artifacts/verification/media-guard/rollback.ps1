param(
    [string]$Workspace = ""
)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}
$baseline = "8a54621"
$files = @(
    "core/agent.py",
    "core/actions/media.py",
    "core/verifier.py",
    "tests/test_media_fast_path.py"
)
foreach ($file in $files) {
    & git -C $Workspace restore --source $baseline -- $file
    if ($LASTEXITCODE -ne 0) {
        throw "Rollback failed for $file"
    }
}
Write-Output "Restored media guard source files to $baseline. User data, models, frontend, and voice were not touched."
