$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
Set-Location $root
$baseline = "ceb3447854c6de46e178a77d38212b7edd978d30"
$paths = @(
  "README.md",
  "core/orchestrator.py",
  "core/utils/paths.py",
  "core/voice/tts.py",
  "core/ws_server.py",
  "scripts/package_local_runtime.py"
)
foreach ($path in $paths) {
  git checkout $baseline -- $path
}
foreach ($path in @("scripts/packaged_backend.py", "scripts/build_portable_installer.py", "tests/test_runtime_readiness_and_packaging.py")) {
  if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
}
Write-Output "Rollback restored source files to $baseline. Generated installer/runtime trees were left untouched."
