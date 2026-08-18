# ATLAS Stability & Security Hardening Design

**Goal:** close the post-audit P0/P1 gaps without starting Sprint 15, while preserving the Sprint 8–14 public APIs and existing local-only behavior.

## Design choice

The implementation uses narrow, composable hardening layers instead of a new orchestrator:

1. **CodeEvaluator boundary:** generated Shadow code is statically classified and evaluated only in a disposable subprocess with a restricted environment, temporary working directory, no network policy, bounded output and process-tree termination. Quality score is separate from `SAFE_TO_EVALUATE / REQUIRES_REVIEW / BLOCKED`. A generated module is never registered automatically unless an explicit approval token is supplied.
2. **Cancellable execution:** an instance-owned `ToolExecutor` owns its semaphore. Built-in/external process tools use process-group termination. Legacy in-process tools receive a cooperative cancellation event and are classified as non-hard-cancellable; they are not used for risky generated code. Timeout results include `terminated` and `side_effects_contained` evidence.
3. **Lifecycle and persistence:** a shared `Lifecycle` object coordinates stop/join for background services. A single `atomic_json_write` helper performs temp-write, flush/fsync, replace and directory flush where supported. Stores use bounded retention/importance policies.
4. **Security services:** canonical `core/security/redaction.py` is the only secret scrubber. `core/network_guard.py` validates every redirect hop and resolved IP. Shell execution uses argument arrays and an explicit high-risk gate. WS defaults to loopback, per-session token, Origin checks, rate limiting and protected mutation endpoints.
5. **Trust boundary:** execution, observation and verification become distinct result types. A provider callback cannot self-certify a consequential action. Proactive ACT uses the existing Capability Engine/Risk Gate/checkpoint/observer path.

## Alternatives considered

- A full Windows restricted-token Job Object for every Python Tool: stronger isolation, but incompatible with locally-defined test tools and existing Tool APIs. The design uses subprocess isolation for generated/external tools and an explicit cooperative legacy path.
- A new global supervisor/orchestrator: rejected because it duplicates Cognitive Core ownership. Lifecycle is a reusable utility consumed by current owners.
- Replacing all JSON stores with SQLite: durable, but too broad for this remediation. Atomic bounded JSON is compatible and sufficient for current stores.

## Data contracts

- `SecurityDecision`: `SAFE_TO_EVALUATE`, `REQUIRES_REVIEW`, `BLOCKED`.
- `EvaluationReport`: `quality_score`, `security_decision`, `execution`, `registration_allowed`.
- `ExecutionResult`, `ObservationResult`, `VerificationResult` remain separate and are required by consequential proactive paths.
- Redaction returns safe copies recursively and never mutates caller-owned objects.

## Error and shutdown behavior

Timeout/cancel must terminate owned subprocess trees and verify exit. A non-hard-cancellable legacy callable returns an explicit containment warning and is never used for generated code. Shutdown signals all lifecycle events, flushes stores, joins workers and reports unfinished work as incomplete rather than successful.

## Testing strategy

Tests are classified as UNIT, INTEGRATION, LIVE and ADVERSARIAL. New tests cover reflection/subprocess/socket/env/filesystem/process-spawn attempts, post-timeout writes, command injection, redirect/DNS/IP SSRF, cross-component secret leakage, WS auth/origin/rate limits, crash-safe persistence, lifecycle joins, semaphore isolation, TTS FIFO/interrupt, verification trust and proactive authority. Existing Sprint 8–14 suites remain unchanged except where a prior flaky test is made deterministic.

