# Sprint 13 — ATLAS Cognitive Core

## Runtime identity

`ATLAS / АТЛАС` is the canonical runtime identity. `JARVIS / Джарвис`
remains an input and protocol compatibility alias; existing paths, task IDs,
WebSocket event names, log names, and persisted Sprint 8–12 interfaces are not
renamed.

## Coordination boundary

`core.cognitive.CognitiveOrchestrator` is a typed coordination layer. It owns
continuity state and references the real Tool/Capability registries, Mission
Runtime, Living Context/GoalTracker, relationship hierarchy, Personality,
Attention, Shadow and risk policy. It does not clone their implementation or
introduce a model.

The public turn is:

`address → retrieve relevant references → resolve goal → inspect registry →`
`plan/research/confirm/execute → observe → verify → persist verified result`.

Only structured continuity facts are persisted. There is no field or storage
path for private reasoning, scratchpads or chain-of-thought.

## Addressing and continuity

Address recognition combines edit distance, light phonetics, morphology,
sentence position, punctuation, following command and recent address state.
Non-canonical user forms are learned only after three confirmed uses.

Suspended goals are bounded to five frames and expire after seven days.
Continuation with one referent resumes it; ambiguous continuation asks one
question; a missing or terminal referent is not invented.

## Verification invariant

Neither an action's `ok` value nor process completion is mission success.
`last_verified_result`, learned capability episodes, and the natural success
sentence are produced only after independent desired-state verification.

## Local live scenario

`scripts/sprint13_live_demo.py` creates three local fixture files, resolves an
imperfect ATLAS address, composes the existing filesystem primitives, suspends
and resumes the goal, executes the real actions, observes the disk, verifies
the desired state, records episodes, proves second-run capability reuse and
reopens a fresh cognitive runtime for a contextual follow-up.

The scenario uses no cloud service, secret, frontend change, new model, raw
coordinates, privileged path or destructive external operation.
