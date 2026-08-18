# JARVIS Sprint 9 verification record

Date: 2026-08-17  
Workspace: `E:\jarvis-project`

## Baseline

Command:

```powershell
python -m pytest -q
```

Collected: 161  
Result: **158 passed, 1 failed, 2 skipped**  
Exit status: **1**

The failing regression was
`test_p1_no_local_heavy_escalation`: offline routing collapsed CODER to FAST.

## Modified build

Commands:

```powershell
python -m compileall -q core tests\test_sprint9.py
python -m pytest -q
```

Collected: 179  
Result: **177 passed, 0 failed, 2 skipped**  
Exit statuses: **0, 0**

The two skips are the pre-existing optional model-failure scenarios. The full
run emitted two pre-existing `websockets` deprecation warnings.

Targeted post-fix command:

```powershell
python -m pytest -q tests\test_sprint9.py tests\test_p1_sprint.py tests\test_local_only_hotfix.py
```

Literal result: `................................. [100%]`  
Tests: **33 passed**, exit status **0**.

Diff validation:

```powershell
git diff --check -- <Sprint-9 paths>
```

Result: no whitespace errors, exit status **0**. Git reported only the existing
LF-to-CRLF checkout notice.

## Safe live smoke

Command:

```powershell
python scripts\sprint9_smoke.py
```

Exit status: **0**

```json
{
  "scenario": "safe_file_organization",
  "first": {
    "latency_ms": 49.726,
    "acquisition": "composed",
    "llm_calls": 0,
    "tools_used": ["list_files", "file_move", "list_files_recursive"],
    "verified": true,
    "completed": true,
    "episode_id": "a2ce9fc16952421a8b5cf51eef627e90"
  },
  "second": {
    "latency_ms": 24.018,
    "acquisition": "learned",
    "llm_calls": 0,
    "tools_used": ["list_files", "file_move", "list_files_recursive"],
    "verified": true,
    "completed": true,
    "episode_id": "1e2ea3662ce14b8f9b7293639ffe5a86"
  }
}
```

The fixture used a temporary directory, performed no network or system mutation,
and removed itself after verification.

## Delivery and rollback artifacts

- Modified-source archive: `artifacts/sprint9/jarvis-sprint9-source.zip`
- Workspace-vs-HEAD patch: `artifacts/sprint9/workspace-delivery-vs-HEAD.patch`
- SHA-256 record: `artifacts/sprint9/SHA256SUMS.txt`
- Runnable guarded rollback: `scripts/rollback_sprint9.ps1`

The archive was reopened and verified with 22 entries. The patch was parsed by
`git apply --stat`. The rollback script was executed without a commit argument;
it printed its dry plan and changed no files.

The workspace already contained uncommitted Sprint 1–8 work when this sprint
started. Therefore the patch is explicitly a **workspace-vs-HEAD delivery
snapshot**, not a claim that every hunk belongs only to Sprint 9. Commit-level
rollback is deliberately required so pre-existing working changes are not
silently overwritten.
