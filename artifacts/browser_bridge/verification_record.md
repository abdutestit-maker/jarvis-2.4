# Browser Bridge v2.1 Verification Record

Workspace: `E:\\jarvis-project`
Date: `2026-08-17`

## Baseline evidence

Source record: `docs/sprints/SPRINT15_VERIFICATION.md`.

```text
Command: python -m pytest -q
Exit: 0
Literal result: 427 passed, 2 skipped, 0 failed
```

The bridge snapshot and baseline hashes are in
`artifacts/browser_bridge/baseline_manifest.json` and
`artifacts/browser_bridge/original/`.

## Modified-tree regression

Runtime:
`C:\\Users\\WwW\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\python.exe`

```text
Command: python -m pytest -q --disable-warnings
Exit: 0
Literal result: 466 passed, 2 skipped, 0 failed
Capture: artifacts/browser_bridge/full_pytest_after.txt
```

The same current tree with only the new bridge test module ignored:

```text
Command: python -m pytest -q --disable-warnings --ignore=tests/test_browser_bridge.py
Exit: 0
Literal result: 460 passed, 2 skipped, 0 failed
Capture: artifacts/browser_bridge/full_pytest_without_bridge.txt
```

Browser-focused regression:

```text
Command: python -m pytest -q --disable-warnings tests/test_browser_automation.py tests/test_sprint10_browser.py tests/test_browser_bridge.py tests/test_sprint9.py
Exit: 0
Literal result: 35 passed
Capture: artifacts/browser_bridge/targeted_pytest.txt
```

## Contract checks

`tests/test_browser_bridge.py` proves:

- NFC/trim/casefold/whitespace and sorted-field canonicalization;
- versioned `sf1:` selector fingerprints and session sensitivity;
- `FindResult` confidence, summary, alternatives, and DOM hash;
- stale DOM returns `STALE_DOM` with `action_taken=False`;
- `confirm=True` does not authorize a risky action;
- valid grants are bound to action, session, selector fingerprint, and expiry;
- semantic type readback succeeds without returning the typed value.

## Live acceptance

```text
Command: python scripts/browser_bridge_live_demo.py
Input: generated local HTML fixture, Profile name=SAMPLE, Apply settings, Purchase
Exit: 0
Literal result: report.success=true
Report: artifacts/browser_bridge/live/live_demo_report.json
```

Observed live values include `applied:SAMPLE`, blocked risky action
`CONFIRMATION_REQUIRED`, authorized risky action `success=true`, and
`coordinates_present=false`.

## Static and rollback checks

```text
Command: python -m compileall -q core tests scripts
Exit: 0

Command: git diff --check
Exit: 0

Command: scripts/rollback_browser_bridge.ps1 -DryRun -WorkspaceRoot E:\\jarvis-project
Exit: 0
Literal result: two modified integration files would be restored and bridge-owned files removed
```

Patch: `artifacts/browser_bridge/browser_bridge.patch`.

Rollback is runnable with `-Force` for a non-dry restore; without `-Force` it
does not overwrite modified integration files.
