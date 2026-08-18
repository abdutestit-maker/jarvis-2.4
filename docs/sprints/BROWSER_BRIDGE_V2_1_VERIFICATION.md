# Browser Bridge v2.1 Verification

Date: 2026-08-17

## Evidence order

1. Pre-change snapshot and SHA-256 manifest: `artifacts/browser_bridge/baseline_manifest.json`.
2. Browser regression and bridge contract tests.
3. Canonical fingerprint, stale-DOM, and grant-binding tests.
4. Real local Playwright fixture run.
5. Patch, report, and rollback artifacts.

## Results

| Check | Result |
| --- | --- |
| Previous Sprint 15 baseline | 427 passed, 2 skipped, 0 failed |
| Browser regression (`test_browser_automation.py`, `test_sprint10_browser.py`) | 11 passed |
| Bridge contract tests (`test_browser_bridge.py`) | 6 passed |
| Combined browser tests | 17 passed |
| Sprint 9 + browser regression + bridge | 35 passed |
| Full suite after bridge (current workspace) | 466 passed, 2 skipped, 0 failed |
| Local Playwright live fixture | VERIFIED SUCCESS |

## Live proof

The live report at `artifacts/browser_bridge/live/live_demo_report.json`
contains:

- a stable `live-session` identifier and DOM hash;
- semantic input type with verified value readback;
- Apply click followed by observed `applied:SAMPLE` state;
- Purchase with `confirm=True` blocked as
  `CONFIRMATION_REQUIRED` and `action_taken=false`;
- the same Purchase selector authorized only by a matching, unexpired grant;
- `success=true` only for execute → observe → verify;
- `coordinates_present=false`.

The complete full-suite console capture is stored in
`artifacts/browser_bridge/full_pytest_after.txt`. The prior Sprint 15
verification record remains the authoritative historical baseline of 427
passed, 2 skipped; the current workspace also contains additional pre-existing
test modules, so its unchanged-suite comparison (bridge test ignored) is 460
passed, 2 skipped.

## Known limitations

- The in-app Browser tool blocked the local `file://` fixture under its URL
  policy. The live acceptance proof therefore uses the project's real local
  Playwright runtime, not a simulated browser.
- Grant issuance remains an Operator/Risk Gate responsibility. The bridge
  validates grants but never invents one from `confirm=True`.
- Vision and coordinate interaction are intentionally outside this contract;
  semantic DOM selectors remain the primary path.
