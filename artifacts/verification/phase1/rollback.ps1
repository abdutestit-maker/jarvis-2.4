param([string]$Repo = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$Base = "dbbc75a"
$Tracked = @(
  "config/settings.py", "config/settings.example.json", "core/agent.py",
  "core/llm/__init__.py", "core/llm/backend.py", "core/llm/local_qwen.py",
  "core/llm/remote_api.py"
)
git -C $Repo restore --source=$Base -- $Tracked
foreach ($p in @("core/llm/tool_calls.py", "tests/test_native_tool_calls.py")) {
  $full = Join-Path $Repo $p
  if (Test-Path -LiteralPath $full) { [IO.File]::Delete($full) }
}
Write-Output "Rollback restored Phase 1 native tool-calling source to $Base. Phase 0 artifacts, user settings, models and unrelated workspace artifacts were left untouched."
