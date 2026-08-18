# JARVIS Sprint 9 changeset

## Scope

Capability Engine for unknown-task discovery, composition, execution,
desired-state verification, targeted repair and learning. The existing Tool
Registry remains the primitive-operation layer.

## Changed files

### Core integration

- `core/agent.py` — routes unknown work through capability search/composition
  before the Sprint 8 generated-tool fallback; queues failed capabilities.
- `core/orchestrator.py` — persistent mission runtime and interruption facade.
- `core/task_runtime.py` — atomic mission persistence, restore, pause, skip and
  explain-current-step operations.
- `core/model_router.py` — separates requested task role from model availability.
- `core/llm/factory.py` — preserves offline CODER/ANALYST roles while selecting
  the best configured local model.
- `core/capabilities.py` — adds CRITICAL to the existing risk taxonomy.
- `core/safety.py` — recognizes critical destructive-system operations.
- `core/actions/filesystem.py` — adds bounded copy/move/recursive-list primitives.

### New capability layer

- `core/capability_engine.py` — persistent catalog, capability/episode models,
  planner/DAG, structured research, desired-state verifier, execution/repair,
  learning, risk-confidence policy and transaction abstraction.
- `core/platform/windows.py` — Windows provider contract, reliability ladder,
  native primitives and optional WinApp/UIA/vision adapters.
- `core/platform/browser.py` — DOM-first adapter over existing Playwright engine.
- `core/platform/__init__.py` — platform-layer public exports.

### Shadow integration

- `core/shadow/backlog.py` — persistent bounded background backlog and load gate.
- `core/shadow/engine.py` — queues rejected/unstable work for later rehearsal.
- `core/shadow/__init__.py` — exports backlog types.

### Tests and verification

- `tests/test_sprint9.py` — 18 unit/integration scenarios.
- `tests/test_p1_sprint.py` — offline CODER regression expectation.
- `tests/test_local_only_hotfix.py` — offline ANALYST/local-role regression.
- `scripts/sprint9_smoke.py` — disposable unknown-task learn/reuse smoke test.
- `docs/sprints/SPRINT9_VERIFICATION.md` — literal verification record.
- `scripts/rollback_sprint9.ps1` — guarded commit-level rollback.

## Compatibility

No frontend files, network services, databases or model assets were added.
Storage uses atomic local JSON under `data/capabilities`, `data/missions` and the
existing Shadow data directory.

