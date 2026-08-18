# Sprint 11 — Living Context + Proactive Intelligence

## Objective
Build a local, privacy-minimal structured context engine that segments activity,
infers goals/friction from accumulated evidence, learns semantic workflows,
chooses silent/prepare/suggest/act/ask/warn through a configurable score policy,
respects attention/resource budgets, and feeds verified learning into the
existing Capability and Shadow engines.

## Invariants
- Structured metadata only: no raw keystrokes, continuous screenshots, pixels,
  passwords, or private control values.
- Evidence is mandatory for every proactive output.
- LOW + reversible + clear context + permitted autonomy is the maximum ACT path.
- HIGH/CRITICAL proactive actions are suppressed; normal Risk Gate remains final.
- Default autonomy is assistant and default decision is SILENT.
- Semantic actions only; raw coordinate macros are excluded.
- Existing Mission Runtime owns long-running PREPARE work.
- No frontend changes and no new model dependencies.

## Vertical slices
1. Observation normalization, sensitive filtering, current context and episodes.
2. Goal/friction inference, session summaries and return context.
3. Workflow similarity/generalization and Capability Catalog bridge.
4. Proactive scoring, evidence gate, memory, autonomy/computer assistance profiles.
5. Attention and background resource budgets, Shadow priority/quality loop.
6. Integrated safe live fixtures and full regression.

## Verification
`python -m pytest -o addopts='' -q`
`python -m compileall -q core config scripts`
`git diff --check`
`python scripts/sprint11_live_demo.py`
