# Stability & Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** remediate the verified P0/P1 audit findings and produce a fully verified Sprint 14 hardening package without beginning Sprint 15.

**Architecture:** keep existing owners and add focused security, lifecycle, persistence and trust-boundary utilities. Generated code and cancellable external work run in disposable subprocesses; legacy synchronous tools remain API-compatible but are explicitly classified. All persistence and logs pass through atomic and redaction services.

**Tech Stack:** Python 3.11, standard library subprocess/multiprocessing/threading/socket/ipaddress/json, existing pytest, websockets, requests and psutil.

## Global Constraints

- Preserve Sprint 8–14 behavior and existing tests.
- Do not add LLM models.
- Do not modify the frontend.
- Keep execution local and do not persist secrets/private reasoning.
- Do not start Sprint 15.
- Generated code must never gain host RCE from a quality score.

### Task 1: Reproduce and document audit findings

**Files:**
- Create: `docs/audits/RED_TEAM_REMEDIATION.md`
- Create: `tests/test_hardening_audit_reproduction.py`
- Use: `core/shadow/sandbox.py`, `core/shadow/engine.py`, `core/actions/executor.py`, `core/voice/tts_queue.py`, `core/network_guard.py`, `core/ws_server.py`, persistence stores

- [ ] Write tests that demonstrate the current shadow in-process registration, watchdog post-timeout side effect, mutable global semaphore, `shell=True`, redirect gap and missing WS session protection.
- [ ] Run the tests and capture the expected failures/confirmations.
- [ ] Record every claim as CONFIRMED, PARTIALLY CONFIRMED or FALSE POSITIVE, including evidence and planned fix.

### Task 2: Canonical redaction and atomic persistence

**Files:**
- Create: `core/security/__init__.py`
- Create: `core/security/redaction.py`
- Create: `core/security/atomic.py`
- Modify: `core/redact.py`, `core/memory/secret_filter.py`, `core/metacognition/store.py`, `core/metacognition/audit.py`, relationship/proactive/cognitive/shadow stores
- Test: `tests/test_hardening_redaction.py`, `tests/test_hardening_persistence.py`

- [ ] Add failing tests for recursive secret fields, bearer/cookie/private-key/connection-string masking, idempotence and crash-safe temp replacement.
- [ ] Implement the canonical service and compatibility wrappers.
- [ ] Add max-record/TTL/importance compaction to mutable learning stores.
- [ ] Run unit and crash-interruption tests.

### Task 3: CodeEvaluator and explicit security decisions

**Files:**
- Modify: `core/shadow/sandbox.py`, `core/shadow/engine.py`, `core/shadow/__init__.py`
- Create: `core/shadow/evaluator_worker.py`
- Test: `tests/test_hardening_shadow.py`

- [ ] Add failing tests for reflection, process, socket, environment, filesystem, child-process and network attempts.
- [ ] Implement `SecurityDecision`, separate quality score, disposable evaluator, restricted environment, bounded output and process-tree kill.
- [ ] Make generated tool registration require explicit approval and prevent `GeneratedShadowTool.run` from importing arbitrary generated code in-process.
- [ ] Preserve a compatibility result for existing Sprint 8 tests while exposing `registration_allowed=False` for unapproved code.

### Task 4: Real executor watchdog and instance-scoped concurrency

**Files:**
- Modify: `core/actions/executor.py`, `core/actions/base.py`, `core/task_runtime.py`
- Create: `core/actions/process_worker.py`
- Test: `tests/test_hardening_executor.py`

- [ ] Add failing post-timeout-write and executor-isolation tests.
- [ ] Implement `ToolExecutor` with immutable instance semaphore and cancellation-safe release.
- [ ] Implement subprocess execution for tools declaring a cancellable process spec, with process-group/job-tree termination and exit verification.
- [ ] Keep legacy API `execute_tool` delegating to a per-context/runtime executor.

### Task 5: TTS and unified lifecycle

**Files:**
- Modify: `core/voice/tts_queue.py`, `core/voice/tts.py`, `core/living/service.py`, `core/living/monitor.py`, `core/shadow/engine.py`, `core/proactive/proactor.py`, `core/proactive/background_tasks.py`, `core/triggers/monitor.py`, `core/ws_server.py`
- Create: `core/lifecycle.py`
- Test: `tests/test_hardening_lifecycle.py`, `tests/test_hardening_tts.py`

- [ ] Add failing FIFO, stop/requeue, interrupt and concurrent shutdown tests.
- [ ] Replace lock-held sleeps/polling with condition/event waits.
- [ ] Add `start`, `stop`, `join`/`stopped` to current services and make shutdown flush then join.
- [ ] Run lifecycle stress tests and verify no worker remains alive.

### Task 6: Shell, SSRF, WS and trust boundary

**Files:**
- Modify: `core/actions/app_control.py`, `core/actions/web_fetch.py`, `core/actions/web_search.py`, `core/actions/weather.py`, `core/network_guard.py`, `core/ws_server.py`, `core/platform/browser.py`, `core/platform/windows.py`, `core/proactive/proactive.py`, `core/living/proactive.py`, `core/verifier.py`
- Create: `core/trust.py`
- Test: `tests/test_hardening_network_ws.py`, `tests/test_hardening_trust.py`

- [ ] Add failing injection, redirect/IP, WS auth/origin/rate-limit and provider self-certification tests.
- [ ] Remove `shell=True`; reject command strings and use arrays/high-risk confirmation.
- [ ] Revalidate every redirect and resolved destination with size/time limits.
- [ ] Add localhost token/origin/rate-limit protections and protect settings mutation.
- [ ] Separate execution/observation/verification and route proactive ACT through existing risk/checkpoint path.
- [ ] Classify unsupported platform methods explicitly.

### Task 7: Cleanup, ownership, taxonomy and performance

**Files:**
- Modify: `.gitignore`, `docs/architecture/OWNERSHIP.md`
- Create: `docs/testing/TEST_TAXONOMY.md`, `scripts/hardening_measure.py`, `scripts/hardening_live_demo.py`
- Modify/archive: `artifacts/archive/`

- [ ] Measure repository size and runtime metrics before cleanup.
- [ ] Archive duplicated extracted source trees with checksums and remove only verified duplicates.
- [ ] Document ownership map and test taxonomy.
- [ ] Run performance measurement and safe live demo.

### Task 8: Full verification and rollback package

**Files:**
- Create: `artifacts/hardening_*`
- Create: `scripts/rollback_hardening.ps1`
- Create: `artifacts/hardening_verification_record.json`
- Create: `docs/audits/RED_TEAM_REMEDIATION.md` (final evidence)

- [ ] Run full pytest, adversarial, concurrency, crash, voice, live operator, isolated Shadow evaluation, compileall and `git diff --check`.
- [ ] Reopen and validate modified artifact, patch, verification record and rollback.
- [ ] Record baseline/final counts, audit classifications, limitations, hashes and exact exit statuses.
- [ ] Confirm Sprint 15 was not started.

