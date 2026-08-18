# Sprint 10 Task List

- [x] Baseline and approved specification
  - Acceptance: Voice smoke passes; full pytest result and source hashes recorded.
  - Verify: `artifacts/sprint10/baseline_pytest.txt`, baseline manifest.

- [x] Windows semantic automation + application discovery
  - Acceptance: real UIA tree/find/invoke/set/select/toggle/scroll/wait operations;
    AppExplorer builds a semantic map and AppKnowledge persists atomically.
  - Verify: focused unit tests plus a real Windows window inspection.

- [x] Browser DOM provider
  - Acceptance: open/navigate/read/find/click/type/download/wait/extract/inspect_dom
    work by DOM selectors without screenshot clicking.
  - Verify: Playwright against a local HTML fixture.

- [x] Trusted software and installer pipeline
  - Acceptance: winget/official/GitHub ranking, type/architecture/signature checks,
    MSI/EXE/ZIP handling, installed-version and launch/window verification.
  - Verify: resolver/installer tests and live official app install.

- [x] Reference/video/state-diff/foreground
  - Acceptance: text/image/web/video inputs produce desired state without click
    replay; adaptive keyframes; semantic diff; foreground restoration.
  - Verify: unit tests and local generated video fixture.

- [x] Capability Engine operator integration
  - Acceptance: execute → observe → verify → targeted repair → learn; interruption
    state; action trace; no completion from `ActionResult.ok` alone.
  - Verify: integration tests including partial mismatch and secret filtering.

- [x] Safe live mission and second-run reuse
  - Acceptance: official free app is really installed/configured/verified; second
    run reuses AppKnowledge/CapabilityEpisode with fewer discovery steps.
  - Verify: archived literal command output, UI tree, state evidence and timings.

- [x] Final verification and rollback
  - Acceptance: full tests/compileall/diff pass; patch, verification record and
    executed rollback are present; modified state is re-applied and reverified.
