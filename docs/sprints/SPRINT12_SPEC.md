# Sprint 12 — Personality + Relationship Layer

## Objective

Add a persistent, privacy-minimal relationship layer without replacing Sprint 9–11,
the Capability Engine, Shadow Engine, Risk Gate, or voice runtime.

## Contracts

- `core.personality.PersonalityEngine` loads typed `IdentityProfile` and
  `PersonalityProfile` data and delegates context-sensitive style decisions to
  `CommunicationAdapter` and `HumorPolicy`.
- `core.memory.relationship.RelationshipMemoryStore` persists only interaction
  preferences and task-class outcomes. Every record includes `fact`, `source`,
  `confidence`, `last_confirmed`, and `importance`.
- `PreferenceLearner` learns explicit communication preferences and aggregate
  accepted/rejected/ignored suggestion outcomes; raw prompts and credentials are
  not written to the relationship profile.
- `MemoryHierarchy` separates working, session, long-term, and relationship
  layers and renders only a bounded relevant context.
- Existing public signatures remain backward compatible; new arguments are
  optional and new behavior is additive.

## Runtime flow

`user input → explicit preference observation → current Living Context → relevant
relationship retrieval → style profile → compact system fragment → response →
bounded session memory`

Sprint 11 suggestion outcomes are recorded through one method into both the
existing proactive cooldown memory and the relationship learner.

## Privacy and retention

- Local JSON only; no network or model additions.
- Secret/raw-event filtering reuses the canonical memory filter.
- Sensitive profile categories and credential-like data are discarded.
- Expired records are excluded immediately and removed by `prune()`.
- Retrieval is relevance-ranked and capped at four relationship records.

## Acceptance

- Repeated short-answer preference results in a short style profile.
- Accepted task-class help increases delegation confidence.
- A newer explicit preference supersedes the previous style and survives restart.
- High-confidence unfinished context can produce one contextual startup greeting.
- The entire Python suite and Russian Piper smoke remain green.

