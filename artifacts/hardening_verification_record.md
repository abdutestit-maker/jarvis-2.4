# Stability hardening verification record

Workspace: `E:\jarvis-project`  
Environment: Windows, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`.

## Baseline (before hardening)

Command:
```powershell
python -m pytest -o addopts='' -q
```
Exit status: `1`  
Literal result: `412 passed, 1 failed, 2 skipped, 2 warnings in 89.43s`  
Failure: `tests/test_ws_server.py::test_ws_command_roundtrip_and_confirmation` (confirmation dispatch race). This was reproduced and fixed by awaiting the executor future.

## Modified verification

Command: `python -m pytest -o addopts='' -q`  
Exit status: `0`  
Literal result: `427 passed, 2 skipped, 2 warnings in 49.54s`.

Command: `python -m pytest -o addopts='' -q tests/test_hardening_*.py` (PowerShell-expanded file list)  
Exit status: `0`  
Literal result: `14 passed in 1.60s`.

Command: `python -m compileall -q core tests scripts`  
Exit status: `0`.

Command: `git diff --check`  
Exit status: `0` (only CRLF normalization warnings from the existing Windows worktree).

## Behavioral probes

* `scripts/voice_runtime_smoke.py artifacts/hardening_voice_smoke.wav` → exit `0`, `success: true`, 22,050 Hz mono, 3.14 s.
* `scripts/sprint10_live_demo.py --fresh-knowledge` → exit `0`, `verified: true`; Notepad++ installer checks all true, UIA controls `68`, final desired state true, second run reused knowledge/episode with zero additional research/discovery.
* `CodeEvaluator` fixture → exit `0`, `quality_score: 90`, `security_decision: SAFE_TO_EVALUATE`, isolated structured result.
* `scripts/hardening_stress.py` → exit `0`, `executor_results: 24`, `executor_failures: 0`, `tts_stopped: true`, `bounded_records: 32`.
* `scripts/hardening_crash_probe.py` → exit `0`, `child_exit: -15`, `json_valid_after_termination: true`.
* `scripts/rollback_stability_hardening.ps1` (hash-restore probe) → exit `0`, `MATCH=True`.

Full literal command output is retained in the sibling `hardening_*.txt` files. The source snapshot manifest contains 51 file hashes; the review patch is `hardening.patch`.
