param([string]$Repo = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$Base = "d6b467473f25c5ccc26877417f90d7836457bc0c"
$Tracked = @(
  "README.md",
  "config/settings.py", "config/settings.example.json",
  "core/agent.py", "core/brain/bootstrap.py", "core/llm/factory.py",
  "core/llm/local_qwen.py", "core/metacognition/engine.py",
  "core/metacognition/freshness.py", "core/orchestrator.py",
  "core/utils/model_manager.py", "core/ws_server.py", "main.py",
  "jarvis/scripts/wsProtocol.test.ts", "jarvis/src-tauri/src/main.rs",
  "jarvis/src/App.tsx", "jarvis/src/hooks/useBackendBridge.ts",
  "jarvis/src/integrations/wsBackend.ts", "jarvis/src/integrations/wsProtocol.ts",
  "jarvis/src/operator/OperatorShell.tsx", "jarvis/src/types/index.ts",
  "tests/test_conversation_latency.py"
)
git -C $Repo restore --source=$Base -- $Tracked
foreach ($p in @(
  "config/models_manifest.json", "core/llm/hardware_profile.py",
  "docs/CODEX_HANDOFF.md", "docs/JARVIS_REBUILD_PLAN.md",
  "docs/PHASE0_IMPLEMENTED.md", "tests/test_hardware_profile.py",
  "tests/test_model_manager.py"
)) {
  $full = Join-Path $Repo $p
  if (Test-Path -LiteralPath $full) { Remove-Item -LiteralPath $full -Force }
}
Write-Output "Rollback restored Phase 0 source to $Base. User settings.json, models and unrelated artifacts were left untouched."
