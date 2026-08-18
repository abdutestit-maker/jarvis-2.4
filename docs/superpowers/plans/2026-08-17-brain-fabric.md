# Brain Fabric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provider-independent, privacy-aware semantic model orchestration while preserving ATLAS identity and all existing execution safeguards.

**Architecture:** Build an additive `core.brain` package around existing LLM backends, then bridge it into Cognitive Core, Council, Agent, self-model and Shadow. Configuration is reloadable and contains secret references only.

**Tech Stack:** Python 3.11, Pydantic 2, requests, llama-cpp-python, pytest, standard-library loopback HTTP server.

## Global Constraints

- Preserve Capability Engine, Cognitive Core, Metacognition, Living Context, Shadow, Operator, Personality, Memory, Voice and security hardening.
- Do not redesign frontend.
- Default to local-first and cloud disabled.
- Do not expose hidden reasoning or allow model output to bypass Risk Gate, Capability Engine or verification.
- Do not persist or log API keys.

---

### Task 1: Typed provider boundary and secure configuration

**Files:** create `core/brain/models.py`, `core/brain/provider.py`, `core/brain/providers.py`, `core/brain/config.py`, `core/brain/secrets.py`; test `tests/test_sprint15_providers.py` and `tests/test_sprint15_security.py`.

- [ ] Write contract/custom endpoint/secret redaction tests and run them to observe missing-module failures.
- [ ] Implement immutable roles, capabilities, requests, routes and results.
- [ ] Implement provider adapters sharing the OpenAI-compatible transport.
- [ ] Implement atomic hot-reload config with `api_key_ref`, then rerun targeted tests.

### Task 2: Health, semantic routing and fallback

**Files:** create `core/brain/health.py`, `core/brain/routing.py`, `core/brain/fabric.py`; test `tests/test_sprint15_routing.py`.

- [ ] Write failing tests for role selection, LOCAL_ONLY, SENSITIVE policy, breaker and bounded fallback.
- [ ] Implement provider/model health metrics and cooldown.
- [ ] Implement policy filters, deterministic scoring, structured reason codes and fallback chains.
- [ ] Implement mission-bound generation/stream/cancel and verify targeted tests.

### Task 3: Context, structured output, critic and local lifecycle

**Files:** create `core/brain/context.py`, `core/brain/structured.py`, `core/brain/critic.py`, `core/brain/local_models.py`, `core/brain/benchmark.py`; test `tests/test_sprint15_context.py`.

- [ ] Write failing tests for priority-preserving budgets, schema rejection, critic verdicts, GGUF inspection and benchmark metrics.
- [ ] Implement each focused component with bounded inputs and no executable output path.
- [ ] Run targeted tests, refactor only after green.

### Task 4: Existing-runtime integration

**Files:** modify `config/settings.py`, `config/settings.example.json`, `core/model_router.py`, `core/orchestrator.py`, `core/router/council.py`, `core/agent.py`, `core/cognitive/orchestrator.py`, `core/cognitive/self_model.py`, `core/shadow/engine.py`; test `tests/test_sprint15_integration.py`.

- [ ] Write failing compatibility tests proving Cognitive Core ownership, identity propagation, self-model facts and local Shadow policy.
- [ ] Add BrainPolicy settings and construct one shared fabric in Orchestrator.
- [ ] Bridge fabric routes/backends into existing ModelRouter, Council and Agent without changing tool execution.
- [ ] Verify Sprint 15 integration tests and focused older regressions.

### Task 5: Live demo, performance and rollback

**Files:** create `scripts/sprint15_live_demo.py`, `scripts/measure_sprint15_performance.py`, `scripts/rollback_sprint15.ps1`, Sprint 15 artifacts.

- [ ] Start two real loopback OpenAI-compatible providers and exercise FAST/REASONING/CODER routes.
- [ ] Stop the primary, measure bounded fallback, verify identity and LOCAL_ONLY zero-egress behavior.
- [ ] Hot-add and remove a provider through JSON, then verify runtime continuity.
- [ ] Measure cold import, simple chat, failover, local load/warm inference where available, and RAM.
- [ ] Run the full test suite and record literal commands, output and exit statuses.
- [ ] Generate and reopen the patch, verification record and rollback script; execute rollback in dry-run verification mode.

