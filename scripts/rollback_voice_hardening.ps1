[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [string]$VoiceHardeningCommit
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspace

if ([string]::IsNullOrWhiteSpace($VoiceHardeningCommit)) {
    Write-Output "Rollback plan: git revert --no-edit <VOICE_HARDENING_COMMIT>"
    Write-Output "No commit argument supplied; no files were changed."
    exit 0
}

git cat-file -e "$VoiceHardeningCommit`^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "VoiceHardeningCommit is not a valid local commit: $VoiceHardeningCommit"
}
git diff --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Working tree has unstaged changes. Preserve or commit them first."
}
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Index has staged changes. Preserve or commit them first."
}

if ($PSCmdlet.ShouldProcess($workspace, "Revert Voice Hardening commit $VoiceHardeningCommit")) {
    git revert --no-edit $VoiceHardeningCommit
    if ($LASTEXITCODE -ne 0) {
        throw "git revert failed; inspect the repository and resolve the revert."
    }
    python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Rollback completed, but the regression suite reported failures."
    }
}
