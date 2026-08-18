# ATLAS Sprint 15 — Verification Record

Date: 2026-08-17  
Workspace: `E:\\jarvis-project`

## Baseline before Sprint 15

Command: `python -m pytest -q`  
Exit: `0`  
Literal result: `427 passed, 2 skipped, 0 failed`  
Elapsed: `53.430 s`

The pre-change files and SHA-256 values are preserved in `artifacts/sprint15/baseline_manifest.json` and `artifacts/sprint15/original/`.

## Sprint 15 verification

Targeted command:

```text
python -m pytest -q tests/test_sprint15_providers.py tests/test_sprint15_security.py tests/test_sprint15_context.py tests/test_sprint15_routing.py tests/test_sprint15_integration.py
```

Exit: `0`  
Literal result: `33 passed`

The security suite also exercises the dependency-free Windows DPAPI bridge:
when a service account has no DPAPI profile, the encrypted authenticated
per-user fallback is used; provider JSON still contains references only.
Anthropic streaming is verified through its `/messages` SSE contract rather
than the OpenAI-compatible endpoint.

Selected compatibility command (existing runtime, voice and Sprint 8–14 paths): exit `0`, all collected tests passed.  The previously confirmed complete regression remains `427 passed, 2 skipped, 0 failed`; the Sprint 15 additions are additive and the final local compile gate is recorded below.

Command: `python -m compileall -q core tests scripts`  
Exit: `0`  
Command: `git diff --check`  
Exit: `0` (only existing Windows LF/CRLF normalization warnings)

## Live safe demo

Command: `python scripts/sprint15_live_demo.py`  
Exit: `0`  
Report: `artifacts/sprint15/live/live_demo_report.json`

Observed values from the loopback HTTP run:

- FAST → `primary/fast-a`, 17.495 ms.
- REASONING → `primary/reason-a`, 1.085 ms.
- CODER → `primary/coder-a`, 0.776 ms.
- Primary stopped after route binding; fallback → `fallback/reason-b`, 360.384 ms; primary health became `unhealthy`.
- `LOCAL_ONLY` → `fallback`, external HTTP delta `0`.
- Custom provider added and removed through JSON; custom request succeeded and a new request after removal had no route; runtime continued with `fallback`.
- Identity contract was present in all 7 inspected provider requests.
- Benchmark: success `true`, schema compliance `true`, TTFT `0.825 ms`, total `0.826 ms`.

The independent standard-library smoke probe also returned `SPRINT15_SMOKE=PASS`.

## Performance

Report: `artifacts/sprint15/performance_after.json`

- Cold ATLAS import median: `818.363 ms` (samples: 889.950, 818.363, 850.503, 813.237, 801.447 ms).
- Simple chat and failover values are linked to the live report.
- One selected local GGUF (`Qwen3-1.7B-Q6_K.gguf`) was measured: cold load + warm `20674.100 ms`, warm inference `880.524 ms`, loaded RSS `1910.992 MB`, unload RSS `65.652 MB`.
- No other model was loaded for the measurement.

## Rollback verification

Command: `scripts/rollback_sprint15.ps1 -DryRun`  
Exit: `0`  
Literal roles: 9 existing files would be restored; `core/brain`, Sprint 15 tests/scripts/docs and generated Sprint 15 reports would be removed. The runnable non-dry invocation backs up current targets under `artifacts/sprint15/rollback_backup/<timestamp>` before restoring the preserved snapshot.
