# Browser Bridge v2.1

## Scope

This changeset adds the strict, Operator-facing browser boundary without
replacing the existing `BrowserAutomationProvider` or changing the frontend,
voice pipeline, Brain Fabric, or Sprint 8–15 components. The legacy provider
and its `ok`-compatible action results remain available for additive
compatibility; new mutations should use `browser_bridge`.

## Runtime surface

`core/platform/browser_bridge.py` provides:

- `BrowserSession` — runtime identity, URL/title, DOM hash, and observation
  timestamps;
- `FindResult` — semantic selector, selector type, confidence, element
  summary, DOM hash, alternatives, and a grant-ready fingerprint;
- `BrowserPolicy` — risk assessment and grant validation;
- `ConfirmationGrant` — action/session/selector/expiry-bound authorization;
- `BrowserActionResult` — formal execute/observe/verify result with `ok` as an
  additive alias;
- `BrowserBridge` — open, navigate, observe, semantic find, read/type/click,
  wait, extract, download, and close.

`core/actions/browser_bridge.py` exposes the bridge through the existing action
registry as `browser_bridge`. Its `confirm` input is retained for compatibility
but is deliberately ignored as an authorization signal.

## Canonical selector fingerprint

`canonical_selector_fingerprint()` is the single implementation used by the
policy boundary and the bridge. It hashes this versioned payload:

```json
{"version":1,"selector_type":"role_name","selector_value":{"name":"Apply settings","role":"button"},"session_id":"SESSION","dom_hash":"abc123"}
```

Selector types use Unicode NFC, trimming, and `casefold()`. Selector fields
drop empty values, sort keys, and normalize string whitespace. The payload is
serialized with `ensure_ascii=False`, sorted keys, and compact separators, then
hashed as `sf1:<sha256-hex>`.

## Mutation protocol

Every mutation follows:

```text
Policy → ConfirmationGrant → current DOM hash check → Execute
       → Observe → Verify → BrowserActionResult
```

`success=True` means execution happened and verification succeeded. A stale
`FindResult` returns `STALE_DOM` with `action_taken=False`; the caller must
observe again, re-resolve the semantic selector, obtain any required grant,
and then retry. A risky action without a matching, unexpired grant returns
`CONFIRMATION_REQUIRED`; an invalid or expired grant returns `POLICY_BLOCKED`.

## Verification fixture

`scripts/browser_bridge_live_demo.py` runs the real local Playwright runtime
against a generated HTML fixture. It types a value, applies it, observes the
result, proves a risky purchase is blocked, then proves the same action with a
selector-bound grant. It also records that no raw coordinates entered the
flow. The resulting report is kept at
`artifacts/browser_bridge/live/live_demo_report.json`.

The optional in-app Browser-assisted checker returned a URL-policy block for
the local `file://` fixture. No workaround or external site was used; the
project-runtime Playwright proof is the authoritative live evidence.

## Rollback

`scripts/rollback_browser_bridge.ps1` restores the pre-bridge snapshots for
modified files and removes only bridge-owned new files. It verifies the target
root, supports `-DryRun`, and leaves modified files in place unless `-Force`
is supplied.
