# Sprint 14 — ATLAS Metacognition Engine

## Boundary

The engine stores structured conclusions, source references, freshness,
confidence inputs, contradictions, expectations, observations and decisions.
There is no storage or API field for chain-of-thought, scratchpads or private
reasoning tokens.

## Epistemic model

`Belief` supports `known`, `observed`, `inferred`, `assumed`, `unknown` and
`conflicted` states plus a separate verification status. Evidence has an
explicit source type and `origin_id`; repeated copies of one upstream source
are deduplicated before confidence calculation.

Confidence is computed by `ConfidenceCalibrator` from direct observation,
verification, source reliability, freshness, independent sources, memory
confidence, contradictions, successful episodes and provider uncertainty.
Status-specific confidence caps prevent assumptions or repeated inferences
from silently becoming facts.

## Knowledge acquisition order

`MetacognitionEngine.resolve` uses:

1. fresh verified observation;
2. relevant stored belief;
3. safe local observer;
4. registered capability;
5. research callback;
6. a concise user-facing unknown response.

The existing `RiskConfidencePolicy` remains authoritative before inspection or
action.

## Expectation and correction

Meaningful changes use a typed `Expectation` with expected effect,
verification method and failure indicators. Action return values are not
success. Independent observation is compared with the expectation. A mismatch
creates a `Surprise`, stores a contextual `FailureEpisode`, reduces strategy
confidence and selects a different strategy within the bounded repair limit.

Failure avoidance is scoped to task class plus a privacy-filtered environment
fingerprint. One failure never creates a global blacklist.

## CurrentMindState integration

Sprint 13 state now exposes safe key lists only:

- `known`
- `unknown`
- `uncertain`
- `conflicted`
- `needs_verification`
- `active_epistemic_key`

Natural queries such as “Ты уверен?” and “Откуда ты это знаешь?” are rendered
from current evidence without exposing internal terminology unless technical
details are explicitly requested.

## Audit

`AuditTrail` exports `atlas.metacognition.audit.v1` containing belief
transitions, confidence inputs, provenance, contradictions, expectations,
observations, surprises, strategy changes, verification results and failure
episodes. Secret-shaped fields and private-reasoning keys are removed.
