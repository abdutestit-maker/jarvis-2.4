$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = Join-Path $project 'artifacts/archive/hardening_last_verified'
if (Test-Path $root) { Remove-Item -LiteralPath $root -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $root 'files') | Out-Null
$paths = @(
 '.gitignore','core/actions/app_control.py','core/actions/base.py','core/actions/executor.py',
 'core/actions/filesystem.py','core/actions/web_fetch.py','core/ingest.py','core/living/context.py',
 'core/living/monitor.py','core/living/proactive.py','core/living/service.py','core/memory/secret_filter.py',
 'core/memory/relationship/store.py','core/memory/relationship/learning.py','core/metacognition/store.py',
 'core/metacognition/audit.py','core/metacognition/failures.py','core/network_guard.py','core/operator/adapters.py',
 'core/operator/knowledge.py','core/operator/software.py','core/operator/reference.py','core/platform/windows.py','core/platform/browser.py',
 'core/actions/browser_automation.py','core/proactive/background_tasks.py',
 'core/proactive/proactor.py','core/redact.py','core/security/__init__.py','core/security/atomic.py',
 'core/security/redaction.py','core/shadow/__init__.py','core/shadow/engine.py','core/shadow/patterns.py',
 'core/shadow/sandbox.py','core/skill_forge.py','core/task_runtime.py','core/trust.py','core/utils/model_manager.py',
 'core/voice/tts.py','core/voice/tts_queue.py','core/voice/tts_sanitizer.py','core/ws_server.py','core/lifecycle.py',
 'core/capability_engine.py','docs/audits/RED_TEAM_REMEDIATION.md','scripts/archive_source_snapshots.ps1',
 'scripts/measure_hardening_performance.py','scripts/rollback_stability_hardening.ps1',
 'scripts/hardening_stress.py','scripts/hardening_crash_probe.py'
)
$entries = @()
foreach ($relative in $paths) {
    $source = Join-Path $project $relative
    if (-not (Test-Path -LiteralPath $source)) { continue }
    $target = Join-Path (Join-Path $root 'files') $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
    $entries += [pscustomobject]@{ path = $relative; sha256 = (Get-FileHash $source -Algorithm SHA256).Hash }
}
[pscustomobject]@{ created_at = (Get-Date).ToUniversalTime().ToString('o'); files = $entries } |
    ConvertTo-Json -Depth 6 | Set-Content (Join-Path $root 'manifest.json') -Encoding utf8
Write-Output "SNAPSHOT_FILES=$($entries.Count)"
