param([switch]$Force)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$previous = "308405a"
$current = (& git -C $root rev-parse HEAD).Trim()

if (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
    throw "Workspace root is not a Git checkout: $root"
}
if (-not $Force) {
    Write-Output "Rollback is armed for $current -> $previous. Re-run with -Force to apply."
    exit 2
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $root ("runs\rollback-backups\" + $stamp)
New-Item -ItemType Directory -Force -Path $backup | Out-Null
& git -C $root diff --binary "$previous..$current" -- `
    | Set-Content -LiteralPath (Join-Path $backup "v4.patch") -Encoding utf8

& git -C $root reset --hard $previous
if ($LASTEXITCODE -ne 0) { throw "Git reset failed" }

# Remove only files introduced by this release, all under the verified workspace.
& git -C $root clean -fd -- `
    core/cognitive_kernel core/research_gateway.py tests/test_cognitive_kernel.py `
    core/operator/setup.py scripts/create_jarvis_icon.py tests/test_jarvis4_acceptance_contract.py `
    tests/test_jarvis4_runtime_contract.py THIRD_PARTY_NOTICES.txt `
    artifacts/verification/overnight

$stable = Join-Path $root "jarvis\src-tauri\target\release\bundle\nsis\J.A.R.V.I.S._3.0.0_x64-setup.exe"
if (Test-Path -LiteralPath $stable) {
    $hash = (Get-FileHash -LiteralPath $stable -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Output "Stable installer remains available: $stable"
    Write-Output "Stable installer SHA-256: $hash"
}
Write-Output "Rollback complete: $current -> $previous"
