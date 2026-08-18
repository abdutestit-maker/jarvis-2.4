[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [string]$Sprint9Commit
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspace

if ([string]::IsNullOrWhiteSpace($Sprint9Commit)) {
    Write-Output "Rollback plan: git revert --no-edit <SPRINT9_COMMIT>"
    Write-Output "The commit argument is required for execution; no files were changed."
    exit 0
}

git cat-file -e "$Sprint9Commit`^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Sprint9Commit is not a valid local commit: $Sprint9Commit"
}

git diff --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Working tree has unstaged changes. Preserve or commit them before rollback."
}
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Index has staged changes. Preserve or commit them before rollback."
}

if ($PSCmdlet.ShouldProcess($workspace, "Revert Sprint 9 commit $Sprint9Commit")) {
    git revert --no-edit $Sprint9Commit
    if ($LASTEXITCODE -ne 0) {
        throw "git revert failed; inspect the repository and resolve the revert."
    }

    python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Rollback completed, but the regression suite reported failures."
    }
}
