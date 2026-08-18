# ATLAS Stability & Security Hardening — Red-Team Remediation

Date: 2026-08-17  
Scope: local Windows runtime and the Python backend only. Sprint 15 is not started.

## Reproduction and classification

The audit was treated as a set of hypotheses. The pre-fix tree was inspected with
`rg`, then the relevant behavior was exercised by the adversarial tests in
`tests/test_hardening_*.py` and the existing Sprint 8–14 suites.

| Finding | Classification | Evidence / disposition |
|---|---|---|
| Shadow code could be imported in the host process after a quality score | **CONFIRMED** | `core/shadow/engine.py` imported generated modules and registration was keyed to one score. Host import was removed; evaluation now uses `CodeEvaluator` in an isolated subprocess and registration additionally requires an explicit `SecurityDecision.SAFE_TO_EVALUATE`. |
| Static score acted as a security permission | **CONFIRMED** | Reproduced in the original `SandboxTester`. `quality_score` and `security_decision` are now independent; `BLOCKED`/`REQUIRES_REVIEW` cannot be promoted by quality. |
| Watchdog returned while daemon work continued | **CONFIRMED** | Reproduced with a repeating-write tool. Opt-in blocking/generated tools now run in a cancellable process, process-tree termination is verified, and a post-timeout write test proves the file stops changing. Legacy non-opt-in tools report their limitation explicitly. |
| Global mutable executor semaphore | **CONFIRMED** | Reproduced by changing capacity between requests. Capacity/semaphore now belong to one `ToolExecutor` cached in a runtime context. |
| TTS lock-held sleep and queue races | **CONFIRMED** | Queue code held a mutex while polling/retrying. It now uses a `Condition`, FIFO deque, event-driven pause/interrupt and non-daemon worker. |
| Daemon background loops / implicit shutdown | **CONFIRMED** | Shadow, Proactor, background tasks, Living/trigger monitors, WS and TTS had daemon workers or polling sleeps. They now expose stop/join (or stopped state) and use events/conditions. |
| Non-atomic JSON persistence | **CONFIRMED** | Several stores used temp replacement without flush/fsync or common locking. Mutable stores now route through `core/security/atomic.py`; crash tests validate readable JSON after interruption. |
| Unbounded learning stores | **CONFIRMED** | Relationship/proactive/capability stores had no uniform bound. `BoundedJSONStore` supplies max-record, recency/importance and TTL compaction policy; migrated stores retain important entries. |
| Multiple inconsistent secret filters | **CONFIRMED** | Separate regexes and markers were found in memory, voice and operator paths. `core/security/redaction.py` is now canonical and callers use compatibility adapters only at legacy boundaries. |
| `shell=True` in app control | **CONFIRMED** | URI launching used shell execution. It now uses argument arrays and platform launch APIs with `shell=False`; injection tests cover metacharacters. |
| Redirect/DNS SSRF gaps | **CONFIRMED** | Fetch followed redirects without per-hop validation. Redirects are manual, every hop is checked, private/link-local/loopback and dangerous ports are rejected, and response size/time are bounded. |
| WS unauthenticated mutation/broadcast surface | **PARTIALLY CONFIRMED** | The original server had no token, Origin or rate gate. Optional bearer/query/first-message authentication, Origin allow-list and per-client rate limiting are implemented; deployments still need to set `JARVIS_WS_TOKEN` for non-local clients. |
| Every platform method returned fake success | **FALSE POSITIVE** | Inspection found real native/UIA/DOM operations and structured errors. A narrower issue was **PARTIALLY CONFIRMED**: some actions reported “started” without observation. Provider results now carry `kind` and `observed`, installer launch explicitly requires later verification, and trust verification rejects provider self-certification. |
| Provider callback `verified=True` was an independent proof | **PARTIALLY CONFIRMED** | Proactive paths already had observer/verifier objects, but generic callbacks could self-certify. `core/trust.py` separates execution, observation and verification and rejects same-provider proof. |
| Artifact tree contained duplicate extracted source | **CONFIRMED** | Historical Sprint snapshots contain repeated `core/` trees. They are evidence, not runtime code; cleanup is documented and generated snapshot paths are ignored. Archives/checksums are kept before any removal. |
| One Agent god object / duplicate orchestration | **PARTIALLY CONFIRMED** | `Agent` eagerly composes many services, but ownership is distributed. No broad API rewrite was made; ownership is documented below and hardening uses runtime-scoped dependencies. |

## Security and execution model after remediation

`CodeEvaluator` is the accurate name (not a claim of a complete OS sandbox). It
runs generated source in a disposable directory with `python -I`, a reduced
environment, bounded output and a timeout. Static checks block imports and calls
that would reach processes, sockets, shells, arbitrary files or system paths.
The evaluator never inherits the host module namespace. Automatic registration
requires both `quality_score >= 90` and `SAFE_TO_EVALUATE`; review/block decisions
always win. The isolated runner is the only path for generated Shadow code.

## Ownership map

* `core/cognitive/` coordinates continuity and mind state.
* `core/living/` observes context/resources and schedules proactive decisions.
* `core/capability_engine.py` plans and executes user goals through the Risk Gate.
* `core/metacognition/` records evidence and verification heuristics.
* `core/shadow/` learns patterns and evaluates candidate tools in the isolated runner.
* `core/proactive/` decides whether to suggest/prepare/act; it does not bypass the gate.
* `core/platform/` performs Windows, browser and reference primitives.
* `core/triggers/` owns event monitors.
* `core/orchestrator.py` remains the application coordinator; no second orchestrator was introduced.

## Test taxonomy

* **UNIT** — deterministic component contracts (`tests/test_hardening_*.py`).
* **INTEGRATION** — backend boundaries such as WS, executor and persistence.
* **ADVERSARIAL** — injection, SSRF, secret leakage and post-timeout side effects.
* **LIVE** — opt-in local voice/operator smoke scripts; they are never replaced by mocks.

## Remaining limits

Legacy third-party tools that do not opt into `supports_hard_cancellation` still
use a compatibility thread and receive a cancellation event; they are reported
as non-hard-cancellable. Full Windows restricted-token/Job-Object isolation is
environment-dependent, so `CodeEvaluator` is not advertised as a complete OS
sandbox. WS authentication is optional for backwards-compatible localhost use.

## Verification record

The exact commands and literal outputs are stored in `artifacts/`:

* `hardening_baseline_pytest.txt` — pre-fix reproduction (412 passed, 1 failed, 2 skipped).
* `hardening_targeted_pytest.txt` — hardening/adversarial suite.
* `hardening_full_pytest.txt` — post-fix full regression.
* `hardening_compileall.txt`, `hardening_diff_check.txt` — packaging checks.
* `hardening_live_operator_fresh.txt` — real Notepad++ install/launch/UIA/config
  run with `verified: true` and second-run reuse.
* `hardening_voice_smoke.txt`, `hardening_shadow_isolated.txt` — voice and
  isolated generated-code smokes.
* `hardening_stress.txt`, `hardening_crash_probe.txt` — concurrency and abrupt
  termination probes.

The only comparable runtime baseline captured before code changes is the full
regression duration (89.43 s). After remediation the full suite completed in
47.94 s (the post-fix suite contains 14 additional hardening tests). The local
performance probe reports a median cold import of 825.45 ms, 18.88 MiB RSS and
one thread for the probe process; raw samples are in
`artifacts/hardening_performance_final.json`. Idle service CPU/RAM was not
started during this non-invasive probe, so no fabricated idle number is shown.

Rollback is runnable from `scripts/rollback_stability_hardening.ps1`; it restores
the captured last-verified manifest (with a timestamped backup) and leaves the
pre-existing Sprint 9–14 original snapshots intact. The dry-run and hash-restore
probe are recorded in `artifacts/hardening_rollback_verification.txt`.
<!-- rollback probe -->
